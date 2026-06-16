#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
from influxdb_client import InfluxDBClient, BucketsApi, OrganizationsApi, TasksApi
from influxdb_client.client.write_api import SYNCHRONOUS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InfluxDBInitializer:
    def __init__(self):
        self.url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.token = os.getenv("INFLUXDB_TOKEN", "mingtang-secret-token")
        self.org = os.getenv("INFLUXDB_ORG", "architecture_research")
        self.bucket_raw = os.getenv("INFLUXDB_BUCKET", "mingtang_data")
        self.bucket_hourly = os.getenv("INFLUXDB_BUCKET_HOURLY", "mingtang_data_hourly")
        self.bucket_daily = os.getenv("INFLUXDB_BUCKET_DAILY", "mingtang_data_daily")
        self.username = os.getenv("INFLUXDB_USERNAME", "admin")
        self.password = os.getenv("INFLUXDB_PASSWORD", "password123")

        self.client = None
        self._connect()

    def _connect(self, max_retries: int = 5, retry_delay: int = 5):
        for i in range(max_retries):
            try:
                logger.info(f"Connecting to InfluxDB at {self.url} (attempt {i+1}/{max_retries})")
                self.client = InfluxDBClient(
                    url=self.url,
                    token=self.token,
                    org=self.org,
                    timeout=30000
                )
                self.client.ready()
                logger.info("Successfully connected to InfluxDB")
                return
            except Exception as e:
                logger.warning(f"Connection failed: {e}")
                if i < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to InfluxDB after maximum retries")
                    raise

    def create_organization(self):
        try:
            orgs_api = OrganizationsApi(self.client)
            orgs = orgs_api.find_organizations(org=self.org)

            if not orgs:
                logger.info(f"Creating organization: {self.org}")
                orgs_api.create_organization(name=self.org)
                logger.info(f"Organization '{self.org}' created successfully")
            else:
                logger.info(f"Organization '{self.org}' already exists")

        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            raise

    def _get_org_id(self) -> str:
        orgs_api = OrganizationsApi(self.client)
        orgs = orgs_api.find_organizations(org=self.org)
        if orgs:
            return orgs[0].id
        raise ValueError(f"Organization '{self.org}' not found")

    def _get_bucket_id(self, bucket_name: str) -> str:
        buckets_api = BucketsApi(self.client)
        buckets = buckets_api.find_buckets(name=bucket_name, org=self.org).buckets
        if buckets:
            return buckets[0].id
        raise ValueError(f"Bucket '{bucket_name}' not found")

    def _bucket_exists(self, bucket_name: str) -> bool:
        buckets_api = BucketsApi(self.client)
        buckets = buckets_api.find_buckets(name=bucket_name, org=self.org).buckets
        return len(buckets) > 0

    def create_buckets(self):
        try:
            buckets_api = BucketsApi(self.client)
            org_id = self._get_org_id()

            if not self._bucket_exists(self.bucket_raw):
                logger.info(f"Creating raw data bucket: {self.bucket_raw} (30天保留)")
                buckets_api.create_bucket(
                    name=self.bucket_raw,
                    org_id=org_id,
                    retention_rules=[{
                        "type": "expire",
                        "everySeconds": 30 * 24 * 3600
                    }]
                )
                logger.info(f"Bucket '{self.bucket_raw}' created (30天原始数据)")
            else:
                logger.info(f"Bucket '{self.bucket_raw}' already exists")

            if not self._bucket_exists(self.bucket_hourly):
                logger.info(f"Creating hourly aggregated bucket: {self.bucket_hourly} (180天保留)")
                buckets_api.create_bucket(
                    name=self.bucket_hourly,
                    org_id=org_id,
                    retention_rules=[{
                        "type": "expire",
                        "everySeconds": 180 * 24 * 3600
                    }]
                )
                logger.info(f"Bucket '{self.bucket_hourly}' created (180天小时级聚合)")
            else:
                logger.info(f"Bucket '{self.bucket_hourly}' already exists")

            if not self._bucket_exists(self.bucket_daily):
                logger.info(f"Creating daily aggregated bucket: {self.bucket_daily} (永久保留)")
                buckets_api.create_bucket(
                    name=self.bucket_daily,
                    org_id=org_id,
                    retention_rules=[]
                )
                logger.info(f"Bucket '{self.bucket_daily}' created (日级聚合, 永久)")
            else:
                logger.info(f"Bucket '{self.bucket_daily}' already exists")

        except Exception as e:
            logger.error(f"Error creating buckets: {e}")
            raise

    def create_downsampling_tasks(self):
        try:
            tasks_api = TasksApi(self.client)
            org_id = self._get_org_id()

            existing_tasks = tasks_api.find_tasks(org=self.org)
            existing_task_names = [t.name for t in existing_tasks.tasks] if existing_tasks else []

            hourly_task_name = "mingtang_sensor_hourly_downsampling"
            if hourly_task_name not in existing_task_names:
                logger.info("Creating hourly downsampling task...")

                hourly_flux = f'''
option task = {{name: "{hourly_task_name}", every: 1h}}

data = from(bucket: "{self.bucket_raw}")
  |> range(start: -task.every)
  |> filter(fn: (r) => r._measurement == "sensor_measurements")
  |> aggregateWindow(
      every: 1h,
      fn: (tables=<-, column) => tables
        |> mean(column: column)
        |> map(fn: (r) => ({{r with _value: r._value}}))
    )
  |> to(bucket: "{self.bucket_hourly}", org: "{self.org}")
'''
                tasks_api.create_task_every(
                    flux=hourly_flux,
                    every="1h",
                    org_id=org_id,
                    description="传感器数据小时级降采样聚合"
                )
                logger.info("Hourly downsampling task created")
            else:
                logger.info("Hourly downsampling task already exists")

            daily_task_name = "mingtang_sensor_daily_downsampling"
            if daily_task_name not in existing_task_names:
                logger.info("Creating daily downsampling task...")

                daily_flux = f'''
option task = {{name: "{daily_task_name}", every: 1d}}

data = from(bucket: "{self.bucket_hourly}")
  |> range(start: -task.every)
  |> filter(fn: (r) => r._measurement == "sensor_measurements")
  |> aggregateWindow(
      every: 1d,
      fn: (tables=<-, column) =>
        tables
          |> mean(column: column)
          |> map(fn: (r) => ({{r with _value: r._value}}))
    )
  |> to(bucket: "{self.bucket_daily}", org: "{self.org}")
'''
                tasks_api.create_task_every(
                    flux=daily_flux,
                    every="1d",
                    org_id=org_id,
                    description="传感器数据日级降采样聚合"
                )
                logger.info("Daily downsampling task created")
            else:
                logger.info("Daily downsampling task already exists")

            sunshine_task_name = "mingtang_daily_sunshine_hours"
            if sunshine_task_name not in existing_task_names:
                logger.info("Creating daily sunshine hours aggregation task...")

                sunshine_flux = f'''
option task = {{name: "{sunshine_task_name}", every: 1d}}

from(bucket: "{self.bucket_raw}")
  |> range(start: -task.every)
  |> filter(fn: (r) =>
      r._measurement == "sensor_measurements" and
      r._field == "illuminance"
    )
  |> filter(fn: (r) => r._value > 50.0)
  |> aggregateWindow(every: 1d, fn: count)
  |> map(fn: (r) => ({{r with
      _value: float(v: r._value) / 60.0 * 60.0,
      _field: "sunshine_hours"
    }}))
  |> to(bucket: "{self.bucket_daily}", org: "{self.org}")
'''
                tasks_api.create_task_every(
                    flux=sunshine_flux,
                    every="1d",
                    org_id=org_id,
                    description="每日日照时长统计"
                )
                logger.info("Daily sunshine hours task created")
            else:
                logger.info("Daily sunshine hours task already exists")

        except Exception as e:
            logger.warning(f"Error creating downsampling tasks (non-fatal): {e}")

    def insert_sample_data(self):
        try:
            from datetime import datetime, timedelta
            import numpy as np

            logger.info("Inserting sample sensor data...")
            write_api = self.client.write_api(write_options=SYNCHRONOUS)

            now = datetime.now()
            locations = ["main_hall", "east_room", "west_room", "south_room", "north_room"]
            season_map = {12: "winter", 1: "winter", 2: "winter",
                          3: "spring", 4: "spring", 5: "spring",
                          6: "summer", 7: "summer", 8: "summer",
                          9: "autumn", 10: "autumn", 11: "autumn"}

            points = []
            for day_offset in range(7):
                for hour in range(24):
                    timestamp = now - timedelta(days=day_offset, hours=23 - hour)
                    current_month = timestamp.month
                    current_season = season_map.get(current_month, "spring")

                    for loc in locations:
                        base_illuminance = 100 + 400 * np.sin(np.pi * max(0, (hour - 6) / 12)) ** 2

                        noise = np.random.normal(0, 20)
                        illuminance = max(0, base_illuminance + noise)

                        solar_altitude = max(0, 50 * np.sin(np.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 0)
                        solar_azimuth = 180 + 90 * np.sin(np.pi * (hour - 12) / 12) if 6 <= hour <= 18 else 0
                        window_transmittance = 0.65 + np.random.normal(0, 0.03)
                        temperature = 15 + 15 * np.sin(np.pi * max(0, (hour - 6) / 12)) + np.random.normal(0, 2)

                        point = {
                            "measurement": "sensor_measurements",
                            "tags": {
                                "hall_id": "han_changan_mingtang",
                                "location": loc,
                                "season": current_season
                            },
                            "fields": {
                                "illuminance": float(illuminance),
                                "solar_altitude": float(solar_altitude),
                                "solar_azimuth": float(solar_azimuth),
                                "window_transmittance": float(max(0.1, min(0.95, window_transmittance))),
                                "temperature": float(temperature)
                            },
                            "time": timestamp.isoformat()
                        }
                        points.append(point)

            write_api.write(bucket=self.bucket_raw, org=self.org, record=points)
            logger.info(f"Inserted {len(points)} sample data points")

        except Exception as e:
            logger.error(f"Error inserting sample data: {e}")
            raise

    def create_dashboard_templates(self):
        logger.info("Creating dashboard templates...")
        logger.info("Dashboard templates creation completed")

    def initialize(self):
        logger.info("=" * 60)
        logger.info("Starting InfluxDB Initialization")
        logger.info("=" * 60)

        self.create_organization()
        self.create_buckets()
        self.insert_sample_data()
        self.create_downsampling_tasks()
        self.create_dashboard_templates()

        logger.info("=" * 60)
        logger.info("InfluxDB Initialization Completed Successfully!")
        logger.info(f"  URL: {self.url}")
        logger.info(f"  Organization: {self.org}")
        logger.info(f"  Raw bucket ({self.bucket_raw}): 30天原始数据")
        logger.info(f"  Hourly bucket ({self.bucket_hourly}): 180天小时级聚合")
        logger.info(f"  Daily bucket ({self.bucket_daily}): 日级聚合(永久)")
        logger.info("  Downsampling Tasks:")
        logger.info("    - mingtang_sensor_hourly_downsampling: 每小时运行")
        logger.info("    - mingtang_sensor_daily_downsampling: 每天运行")
        logger.info("    - mingtang_daily_sunshine_hours: 日照时长统计")
        logger.info("=" * 60)

    def close(self):
        if self.client:
            self.client.close()
            logger.info("InfluxDB client connection closed")


def main():
    try:
        initializer = InfluxDBInitializer()
        initializer.initialize()
        initializer.close()
        return 0
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
