#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.database import InfluxDBManager, get_db_manager
from shared.redis_client import RedisClient, get_redis_client
from shared.schemas import SensorDataBatch, SensorDataPoint, RedisChannels

logger = logging.getLogger(__name__)


class SensorService:
    """传感器数据服务，处理数据采集、验证、入库和Redis发布"""

    def __init__(self):
        self.db_manager: InfluxDBManager = get_db_manager()
        self.redis_client: RedisClient = get_redis_client()

    def ingest_sensor_data(self, data_batch: SensorDataBatch) -> Dict[str, Any]:
        """接收并验证传感器数据批次，写入InfluxDB并发布到Redis"""
        try:
            data_points = []
            for point in data_batch.data:
                point_dict = point.model_dump()
                if point_dict["timestamp"] is None:
                    point_dict["timestamp"] = datetime.utcnow()
                data_points.append(point_dict)

            success = self.db_manager.write_sensor_data(data_points)

            if success:
                self.redis_client.publish(
                    RedisChannels.SENSOR_DATA,
                    {
                        "event": "sensor_data_ingested",
                        "count": len(data_points),
                        "hall_id": data_points[0].get("hall_id", "unknown"),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
                logger.info(f"Ingested {len(data_points)} sensor points and published to Redis")
                return {
                    "status": "success",
                    "message": f"成功接收 {len(data_points)} 条传感器数据",
                    "count": len(data_points),
                }
            else:
                return {
                    "status": "error",
                    "message": "写入InfluxDB失败",
                }

        except Exception as e:
            logger.error(f"传感器数据接收错误: {e}")
            return {
                "status": "error",
                "message": f"传感器数据接收错误: {str(e)}",
            }

    def get_sensor_data(
        self,
        hall_id: str = "han_changan_mingtang",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """从InfluxDB查询传感器数据"""
        try:
            data = self.db_manager.query_sensor_data(
                hall_id=hall_id,
                start_time=start_time,
                end_time=end_time,
                location=location,
                fields=fields,
            )
            return data
        except Exception as e:
            logger.error(f"查询传感器数据错误: {e}")
            return []

    def get_latest_sensor_data(
        self,
        hall_id: str = "han_changan_mingtang",
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """查询最近2小时的传感器数据，返回最新一条"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=2)

            data = self.db_manager.query_sensor_data(
                hall_id=hall_id,
                start_time=start_time,
                end_time=end_time,
                location=location,
            )

            if data:
                latest = max(data, key=lambda x: x.get("timestamp", ""))
                return {
                    "status": "success",
                    "data": latest,
                }
            else:
                return {
                    "status": "error",
                    "message": "未找到传感器数据",
                }

        except Exception as e:
            logger.error(f"获取最新传感器数据错误: {e}")
            return {
                "status": "error",
                "message": f"获取最新传感器数据错误: {str(e)}",
            }

    def get_sensor_statistics(
        self,
        hall_id: str = "han_changan_mingtang",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """计算照度统计信息（最大值、最小值、平均值）"""
        try:
            data = self.db_manager.query_sensor_data(
                hall_id=hall_id,
                start_time=start_time,
                end_time=end_time,
            )

            if not data:
                return {
                    "status": "error",
                    "message": "未找到用于统计的传感器数据",
                }

            illuminance_values = [d.get("illuminance", 0) for d in data if "illuminance" in d]

            if illuminance_values:
                stats = {
                    "count": len(illuminance_values),
                    "max_illuminance": max(illuminance_values),
                    "min_illuminance": min(illuminance_values),
                    "avg_illuminance": sum(illuminance_values) / len(illuminance_values),
                    "data_points": len(data),
                }

                locations = set(d.get("location", "") for d in data)
                stats["locations"] = list(locations)

                return {
                    "status": "success",
                    "statistics": stats,
                }
            else:
                return {
                    "status": "error",
                    "message": "未找到照度数据",
                }

        except Exception as e:
            logger.error(f"计算传感器统计信息错误: {e}")
            return {
                "status": "error",
                "message": f"计算统计信息错误: {str(e)}",
            }

    def get_daily_sunshine_hours(
        self,
        hall_id: str,
        date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """计算指定日期的日照时长"""
        try:
            if date is None:
                date = datetime.now()

            sunshine_hours = self.db_manager.calculate_daily_sunshine_hours(hall_id, date)

            return {
                "status": "success",
                "date": date.strftime("%Y-%m-%d"),
                "sunshine_hours": sunshine_hours,
                "hall_id": hall_id,
            }

        except Exception as e:
            logger.error(f"计算日照时长错误: {e}")
            return {
                "status": "error",
                "message": f"计算日照时长错误: {str(e)}",
            }


def get_sensor_service() -> SensorService:
    return SensorService()
