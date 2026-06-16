#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import uuid
import sys
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import paho.mqtt.client as mqtt
from paho.mqtt import publish

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config import shared_settings, load_json_config
from shared.database import get_db_manager, InfluxDBManager
from shared.redis_client import get_redis_client, RedisClient
from shared.schemas import AlertConfig, AlertType, RedisChannels

logger = logging.getLogger(__name__)


class MQTTAlertService:
    def __init__(self):
        self.broker = shared_settings.mqtt_broker
        self.port = shared_settings.mqtt_port
        self.username = shared_settings.mqtt_username
        self.password = shared_settings.mqtt_password
        self.default_topic = shared_settings.mqtt_topic

        self.client: Optional[mqtt.Client] = None
        self.db_manager: InfluxDBManager = get_db_manager()
        self.redis_client: RedisClient = get_redis_client()
        self._connected = False

        self._alarm_config = load_json_config("alarm_params.json")
        self._alert_params = self._alarm_config.get("alert", {})
        self._mqtt_params = self._alarm_config.get("mqtt", {})
        self._recommendations = self._alarm_config.get("recommendations", {})
        self._season_months = self._alert_params.get("season_months", {
            "spring": [3, 4, 5],
            "summer": [6, 7, 8],
            "autumn": [9, 10, 11],
            "fall": [9, 10, 11],
            "winter": [12, 1, 2],
        })
        self._check_interval = self._alert_params.get("check_interval_seconds", 3600)

        self._subscriber_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._sensor_message_counter = 0
        self._last_check_time = time.time()

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
        qos: Optional[int] = None
    ) -> bool:
        try:
            if not self._connected:
                if not self.connect():
                    logger.error("Cannot publish alert: MQTT not connected")
                    return False

            publish_topic = topic or self.default_topic
            publish_qos = qos if qos is not None else self._mqtt_params.get("qos", 1)
            payload = json.dumps(alert_data, ensure_ascii=False, default=str)

            result = self.client.publish(
                topic=publish_topic,
                payload=payload,
                qos=publish_qos,
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
                    min_daily_sunshine_hours=self._alert_params.get("min_daily_sunshine_hours", shared_settings.min_daily_sunshine_hours),
                    alert_season=self._alert_params.get("alert_season", [shared_settings.alert_season]),
                    mqtt_topic=self._mqtt_params.get("topic", shared_settings.mqtt_topic),
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

    def start_redis_subscriber(self):
        if self._subscriber_thread and self._subscriber_thread.is_alive():
            logger.warning("Redis subscriber already running")
            return

        self._stop_event.clear()
        self._subscriber_thread = threading.Thread(
            target=self._redis_subscriber_loop,
            daemon=True,
            name="redis-sensor-subscriber"
        )
        self._subscriber_thread.start()
        logger.info("Redis subscriber thread started")

    def _redis_subscriber_loop(self):
        pubsub = self.redis_client.subscribe(RedisChannels.SENSOR_DATA)
        if pubsub is None:
            logger.error("Failed to subscribe to Redis channel, subscriber thread exiting")
            return

        logger.info(f"Redis subscriber listening on channel: {RedisChannels.SENSOR_DATA}")

        while not self._stop_event.is_set():
            try:
                message = pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    self._handle_sensor_message(message["data"])

                current_time = time.time()
                if current_time - self._last_check_time >= self._check_interval:
                    self._periodic_alert_check()
                    self._last_check_time = current_time

            except Exception as e:
                logger.error(f"Error in Redis subscriber loop: {e}")
                time.sleep(1)

        pubsub.unsubscribe()
        pubsub.close()
        logger.info("Redis subscriber loop ended")

    def _handle_sensor_message(self, data: str):
        try:
            sensor_data = json.loads(data) if isinstance(data, str) else data
            self._sensor_message_counter += 1
            logger.debug(f"Received sensor data #{self._sensor_message_counter}: {sensor_data.get('hall_id', 'unknown')}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse sensor data: {e}")

    def _periodic_alert_check(self):
        try:
            if self._sensor_message_counter > 0:
                logger.info(f"Periodic alert check: {self._sensor_message_counter} sensor messages received since last check")
                self.check_and_send_sunshine_alert(hall_id="han_changan_mingtang")
                self._sensor_message_counter = 0
            else:
                logger.debug("Periodic alert check: no sensor messages received")
        except Exception as e:
            logger.error(f"Error in periodic alert check: {e}")

    def stop_redis_subscriber(self):
        if self._subscriber_thread and self._subscriber_thread.is_alive():
            self._stop_event.set()
            self._subscriber_thread.join(timeout=5)
            logger.info("Redis subscriber thread stopped")

    def get_alert_history(
        self,
        hall_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        return self.db_manager.query_alert_history(hall_id, start_time, end_time, limit)

    def _is_alert_season(self, date: datetime, alert_seasons: List[str]) -> bool:
        month = date.month

        for season in alert_seasons:
            if season.lower() in self._season_months:
                if month in self._season_months[season.lower()]:
                    return True
            elif season.lower() == "all":
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

        recommendations = self._recommendations.get("low_sunshine", [
            "检查窗户纸是否破损或积尘",
            "考虑增加南向窗户面积",
            "优化室内布局减少遮挡",
            "使用粒子群算法进行采光优化",
        ])

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
                "latitude": shared_settings.latitude,
                "longitude": shared_settings.longitude,
                "recommendations": recommendations
            }
        }

        return alert

    def disconnect(self):
        self.stop_redis_subscriber()
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
