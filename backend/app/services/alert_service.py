#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import paho.mqtt.client as mqtt
from paho.mqtt import publish

from ..core.config import settings
from ..core.database import get_db_manager, InfluxDBManager
from ..models.schemas import AlertConfig, AlertType

logger = logging.getLogger(__name__)


class MQTTAlertService:
    def __init__(self):
        self.broker = settings.mqtt_broker
        self.port = settings.mqtt_port
        self.username = settings.mqtt_username
        self.password = settings.mqtt_password
        self.default_topic = settings.mqtt_topic

        self.client: Optional[mqtt.Client] = None
        self.db_manager: InfluxDBManager = get_db_manager()
        self._connected = False

    def connect(self) -> bool:
        try:
            self.client = mqtt.Client(
                client_id=f"mingtang_alert_service_{uuid.uuid4().hex[:8]}",
                clean_session=True
            )

            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish

            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()

            logger.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self._connected = False
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info("MQTT client connected successfully")
        else:
            self._connected = False
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        logger.warning(f"MQTT client disconnected with code {rc}")

    def _on_publish(self, client, userdata, mid):
        logger.debug(f"Message {mid} published successfully")

    def publish_alert(
        self,
        alert_data: Dict[str, Any],
        topic: Optional[str] = None,
        qos: int = 1
    ) -> bool:
        try:
            if not self._connected:
                if not self.connect():
                    logger.error("Cannot publish alert: MQTT not connected")
                    return False

            publish_topic = topic or self.default_topic
            payload = json.dumps(alert_data, ensure_ascii=False)

            result = self.client.publish(
                topic=publish_topic,
                payload=payload,
                qos=qos,
                retain=False
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Alert published to {publish_topic}: {alert_data.get('message', '')}")
                return True
            else:
                logger.error(f"Failed to publish alert: {result.rc}")
                return False

        except Exception as e:
            logger.error(f"Error publishing alert: {e}")
            return False

    def check_and_send_sunshine_alert(
        self,
        hall_id: str,
        date: Optional[datetime] = None,
        config: Optional[AlertConfig] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            if date is None:
                date = datetime.now() - timedelta(days=1)

            if config is None:
                config = AlertConfig(
                    min_daily_sunshine_hours=settings.min_daily_sunshine_hours,
                    alert_season=[settings.alert_season],
                    mqtt_topic=settings.mqtt_topic,
                    hall_id=hall_id
                )

            if not self._is_alert_season(date, config.alert_season):
                logger.info(f"No alert needed: {date.date()} is not in alert season")
                return None

            sunshine_hours = self.db_manager.calculate_daily_sunshine_hours(hall_id, date)

            if sunshine_hours < config.min_daily_sunshine_hours:
                alert = self._create_sunshine_alert(
                    hall_id, date, sunshine_hours, config
                )

                if self.publish_alert(alert, config.mqtt_topic):
                    self.db_manager.write_alert_record(alert)
                    logger.warning(f"Sunshine alert sent: {sunshine_hours:.1f}h < {config.min_daily_sunshine_hours}h")
                    return alert
                else:
                    logger.error("Failed to send sunshine alert")
                    return None
            else:
                logger.info(f"No alert needed: {sunshine_hours:.1f}h >= {config.min_daily_sunshine_hours}h")
                return None

        except Exception as e:
            logger.error(f"Error checking sunshine alert: {e}")
            return None

    def _is_alert_season(self, date: datetime, alert_seasons: List[str]) -> bool:
        month = date.month

        season_ranges = {
            'spring': [3, 4, 5],
            'summer': [6, 7, 8],
            'autumn': [9, 10, 11],
            'fall': [9, 10, 11],
            'winter': [12, 1, 2]
        }

        for season in alert_seasons:
            if season.lower() in season_ranges:
                if month in season_ranges[season.lower()]:
                    return True
            elif season.lower() == 'all':
                return True

        return False

    def _create_sunshine_alert(
        self,
        hall_id: str,
        date: datetime,
        sunshine_hours: float,
        config: AlertConfig
    ) -> Dict[str, Any]:
        alert_id = f"alert_{uuid.uuid4().hex}"

        alert = {
            "alert_id": alert_id,
            "hall_id": hall_id,
            "alert_type": AlertType.LOW_SUNSHINE.value,
            "timestamp": datetime.now(),
            "message": (
                f"【日照不足预警】{date.strftime('%Y年%m月%d日')} "
                f"汉长安明堂日照时长为{sunshine_hours:.1f}小时，"
                f"低于阈值{config.min_daily_sunshine_hours}小时。"
                f"建议检查窗户清洁情况或考虑优化方案。"
            ),
            "sunshine_hours": sunshine_hours,
            "threshold": config.min_daily_sunshine_hours,
            "acknowledged": False,
            "details": {
                "date": date.strftime("%Y-%m-%d"),
                "location": "汉长安明堂遗址",
                "latitude": settings.latitude,
                "longitude": settings.longitude,
                "recommendations": [
                    "检查窗户纸是否破损或积尘",
                    "考虑增加南向窗户面积",
                    "优化室内布局减少遮挡",
                    "使用粒子群算法进行采光优化"
                ]
            }
        }

        return alert

    def get_alert_history(
        self,
        hall_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        return self.db_manager.query_alert_history(hall_id, start_time, end_time, limit)

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self._connected = False
            logger.info("MQTT client disconnected")

    def __del__(self):
        self.disconnect()


def get_alert_service() -> MQTTAlertService:
    service = MQTTAlertService()
    return service
