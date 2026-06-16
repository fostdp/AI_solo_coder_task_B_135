#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Mingtang Lighting Simulation System"
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    app_env: str = os.getenv("APP_ENV", "development")

    influxdb_url: str = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    influxdb_token: str = os.getenv("INFLUXDB_TOKEN", "mingtang-secret-token")
    influxdb_org: str = os.getenv("INFLUXDB_ORG", "architecture_research")
    influxdb_bucket: str = os.getenv("INFLUXDB_BUCKET", "mingtang_data")

    mqtt_broker: str = os.getenv("MQTT_BROKER", "localhost")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_username: Optional[str] = os.getenv("MQTT_USERNAME", None)
    mqtt_password: Optional[str] = os.getenv("MQTT_PASSWORD", None)
    mqtt_topic: str = os.getenv("MQTT_TOPIC", "mingtang/alerts")

    min_daily_sunshine_hours: float = float(os.getenv("MIN_DAILY_SUNSHINE_HOURS", "3.0"))
    alert_season: str = os.getenv("ALERT_SEASON", "winter")

    latitude: float = float(os.getenv("LATITUDE", "34.2658"))
    longitude: float = float(os.getenv("LONGITUDE", "108.9541"))

    cors_origins: list = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
