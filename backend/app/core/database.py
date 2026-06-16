#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.flux_table import FluxRecord

from .config import settings

logger = logging.getLogger(__name__)


class InfluxDBManager:
    _instance: Optional['InfluxDBManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org,
            timeout=30000
        )
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
        self.delete_api = self.client.delete_api()
        self.bucket = settings.influxdb_bucket
        self.org = settings.influxdb_org
        logger.info("InfluxDBManager initialized")

    def write_sensor_data(self, data_points: List[Dict]) -> bool:
        try:
            points = []
            for data in data_points:
                point = Point("sensor_measurements")
                point.tag("hall_id", data.get("hall_id", "han_changan_mingtang"))
                point.tag("location", data.get("location", "unknown"))

                if "illuminance" in data:
                    point.field("illuminance", float(data["illuminance"]))
                if "solar_altitude" in data:
                    point.field("solar_altitude", float(data["solar_altitude"]))
                if "solar_azimuth" in data:
                    point.field("solar_azimuth", float(data["solar_azimuth"]))
                if "window_transmittance" in data:
                    point.field("window_transmittance", float(data["window_transmittance"]))

                timestamp = data.get("timestamp", datetime.utcnow().isoformat())
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                point.time(timestamp, WritePrecision.NS)

                points.append(point)

            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            logger.info(f"Successfully wrote {len(points)} sensor data points")
            return True
        except Exception as e:
            logger.error(f"Error writing sensor data: {e}")
            return False

    def query_sensor_data(
        self,
        hall_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        fields: Optional[List[str]] = None
    ) -> List[Dict]:
        try:
            if start_time is None:
                start_time = datetime.now() - timedelta(days=7)
            if end_time is None:
                end_time = datetime.now()

            flux_query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                    |> filter(fn: (r) => r["_measurement"] == "sensor_measurements")
                    |> filter(fn: (r) => r["hall_id"] == "{hall_id}")
            '''

            if location:
                flux_query += f'|> filter(fn: (r) => r["location"] == "{location}")\n'

            if fields:
                field_filters = " or ".join([f'r["_field"] == "{f}"' for f in fields])
                flux_query += f'|> filter(fn: (r) => {field_filters})\n'

            flux_query += '|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'

            tables = self.query_api.query(flux_query, org=self.org)

            results = []
            for table in tables:
                for record in table.records:
                    results.append(self._record_to_dict(record))

            logger.info(f"Query returned {len(results)} records")
            return results
        except Exception as e:
            logger.error(f"Error querying sensor data: {e}")
            return []

    def write_simulation_result(self, task_id: str, result: Dict) -> bool:
        try:
            point = Point("simulation_results")
            point.tag("task_id", task_id)
            point.tag("hall_id", result.get("hall_id", "han_changan_mingtang"))
            point.tag("sky_model", result.get("sky_model", "perez"))

            point.field("max_illuminance", float(result.get("max_illuminance", 0)))
            point.field("min_illuminance", float(result.get("min_illuminance", 0)))
            point.field("avg_illuminance", float(result.get("avg_illuminance", 0)))
            point.field("uniformity", float(result.get("uniformity", 0)))
            point.field("grid_resolution", int(result.get("grid_resolution", 10)))

            timestamp = result.get("timestamp", datetime.utcnow())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            point.time(timestamp, WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.info(f"Successfully wrote simulation result for task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error writing simulation result: {e}")
            return False

    def write_optimization_result(self, task_id: str, result: Dict) -> bool:
        try:
            point = Point("optimization_results")
            point.tag("task_id", task_id)
            point.tag("hall_id", result.get("hall_id", "han_changan_mingtang"))
            point.tag("algorithm", result.get("algorithm", "pso"))

            point.field("best_fitness", float(result.get("best_fitness", 0)))
            point.field("uniformity", float(result.get("uniformity", 0)))
            point.field("iterations", int(result.get("iterations", 0)))
            point.field("convergence_time", float(result.get("execution_time", 0)))

            point.time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.info(f"Successfully wrote optimization result for task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error writing optimization result: {e}")
            return False

    def write_alert_record(self, alert: Dict) -> bool:
        try:
            point = Point("alert_records")
            point.tag("alert_id", alert["alert_id"])
            point.tag("hall_id", alert.get("hall_id", "han_changan_mingtang"))
            point.tag("alert_type", alert.get("alert_type", "low_sunshine"))

            point.field("message", str(alert.get("message", "")))
            point.field("sunshine_hours", float(alert.get("sunshine_hours", 0)))
            point.field("threshold", float(alert.get("threshold", 0)))
            point.field("acknowledged", bool(alert.get("acknowledged", False)))

            point.time(alert.get("timestamp", datetime.utcnow()), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.info(f"Successfully wrote alert record {alert['alert_id']}")
            return True
        except Exception as e:
            logger.error(f"Error writing alert record: {e}")
            return False

    def query_alert_history(
        self,
        hall_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        try:
            if start_time is None:
                start_time = datetime.now() - timedelta(days=30)
            if end_time is None:
                end_time = datetime.now()

            flux_query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                    |> filter(fn: (r) => r["_measurement"] == "alert_records")
            '''

            if hall_id:
                flux_query += f'|> filter(fn: (r) => r["hall_id"] == "{hall_id}")\n'

            flux_query += f'|> sort(columns: ["_time"], desc: true)\n|> limit(n: {limit})'

            tables = self.query_api.query(flux_query, org=self.org)

            results = []
            for table in tables:
                for record in table.records:
                    results.append(self._record_to_dict(record))

            return results
        except Exception as e:
            logger.error(f"Error querying alert history: {e}")
            return []

    def calculate_daily_sunshine_hours(
        self,
        hall_id: str,
        date: datetime
    ) -> float:
        try:
            start_time = datetime(date.year, date.month, date.day, 0, 0, 0)
            end_time = start_time + timedelta(days=1)

            flux_query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                    |> filter(fn: (r) => r["_measurement"] == "sensor_measurements")
                    |> filter(fn: (r) => r["hall_id"] == "{hall_id}")
                    |> filter(fn: (r) => r["_field"] == "solar_altitude")
                    |> filter(fn: (r) => r["solar_altitude"] > 0)
                    |> count()
            '''

            tables = self.query_api.query(flux_query, org=self.org)

            total_hours = 0.0
            for table in tables:
                for record in table.records:
                    total_hours += record.get_value()

            return total_hours
        except Exception as e:
            logger.error(f"Error calculating sunshine hours: {e}")
            return 0.0

    def _record_to_dict(self, record: FluxRecord) -> Dict:
        result = {
            "timestamp": record.get_time().isoformat() if record.get_time() else None,
            "measurement": record.get_measurement(),
        }

        for key, value in record.values.items():
            if not key.startswith("_") and key not in ["result", "table"]:
                result[key] = value

        field = record.get_field()
        value = record.get_value()
        if field and field not in result:
            result[field] = value

        return result

    def close(self):
        if self.client:
            self.client.close()
            logger.info("InfluxDB client closed")


def get_db_manager() -> InfluxDBManager:
    return InfluxDBManager()
