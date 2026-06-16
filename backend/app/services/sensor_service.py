#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..core.database import get_db_manager, InfluxDBManager
from ..models.schemas import SensorDataPoint, SensorDataBatch

logger = logging.getLogger(__name__)


class SensorService:
    def __init__(self):
        self.db_manager: InfluxDBManager = get_db_manager()

    def ingest_sensor_data(self, data_batch: SensorDataBatch) -> Dict[str, Any]:
        try:
            data_points = []
            for point in data_batch.data:
                point_dict = point.model_dump()
                if point_dict["timestamp"] is None:
                    point_dict["timestamp"] = datetime.utcnow()
                data_points.append(point_dict)

            success = self.db_manager.write_sensor_data(data_points)

            if success:
                return {
                    "status": "success",
                    "message": f"Successfully ingested {len(data_points)} sensor data points",
                    "count": len(data_points)
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to write sensor data to InfluxDB"
                }

        except Exception as e:
            logger.error(f"Error ingesting sensor data: {e}")
            return {
                "status": "error",
                "message": f"Error ingesting sensor data: {str(e)}"
            }

    def get_sensor_data(
        self,
        hall_id: str = "han_changan_mingtang",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        try:
            data = self.db_manager.query_sensor_data(
                hall_id=hall_id,
                start_time=start_time,
                end_time=end_time,
                location=location,
                fields=fields
            )
            return data
        except Exception as e:
            logger.error(f"Error querying sensor data: {e}")
            return []

    def get_latest_sensor_data(
        self,
        hall_id: str = "han_changan_mingtang",
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=2)

            data = self.db_manager.query_sensor_data(
                hall_id=hall_id,
                start_time=start_time,
                end_time=end_time,
                location=location
            )

            if data:
                latest = max(data, key=lambda x: x.get("timestamp", ""))
                return {
                    "status": "success",
                    "data": latest
                }
            else:
                return {
                    "status": "error",
                    "message": "No sensor data found"
                }

        except Exception as e:
            logger.error(f"Error getting latest sensor data: {e}")
            return {
                "status": "error",
                "message": f"Error getting latest sensor data: {str(e)}"
            }

    def get_sensor_statistics(
        self,
        hall_id: str = "han_changan_mingtang",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        try:
            data = self.db_manager.query_sensor_data(
                hall_id=hall_id,
                start_time=start_time,
                end_time=end_time
            )

            if not data:
                return {
                    "status": "error",
                    "message": "No sensor data found for statistics"
                }

            illuminance_values = [d.get("illuminance", 0) for d in data if "illuminance" in d]

            if illuminance_values:
                stats = {
                    "count": len(illuminance_values),
                    "max": max(illuminance_values),
                    "min": min(illuminance_values),
                    "avg": sum(illuminance_values) / len(illuminance_values),
                    "data_points": len(data)
                }

                locations = set(d.get("location", "") for d in data)
                stats["locations"] = list(locations)

                return {
                    "status": "success",
                    "statistics": stats
                }
            else:
                return {
                    "status": "error",
                    "message": "No illuminance data found"
                }

        except Exception as e:
            logger.error(f"Error calculating sensor statistics: {e}")
            return {
                "status": "error",
                "message": f"Error calculating statistics: {str(e)}"
            }

    def get_daily_sunshine_hours(
        self,
        hall_id: str,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        try:
            if date is None:
                date = datetime.now()

            sunshine_hours = self.db_manager.calculate_daily_sunshine_hours(hall_id, date)

            return {
                "status": "success",
                "date": date.strftime("%Y-%m-%d"),
                "sunshine_hours": sunshine_hours,
                "hall_id": hall_id
            }

        except Exception as e:
            logger.error(f"Error calculating sunshine hours: {e}")
            return {
                "status": "error",
                "message": f"Error calculating sunshine hours: {str(e)}"
            }


def get_sensor_service() -> SensorService:
    return SensorService()
