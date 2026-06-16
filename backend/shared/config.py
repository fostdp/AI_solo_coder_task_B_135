import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_json_config(filename: str) -> Dict[str, Any]:
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        logger.warning(f"Config file not found: {filepath}, using defaults")
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


class SharedSettings(BaseSettings):
    app_env: str = os.getenv("APP_ENV", "development")

    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD", None)

    influxdb_url: str = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    influxdb_token: str = os.getenv("INFLUXDB_TOKEN", "mingtang-secret-token")
    influxdb_org: str = os.getenv("INFLUXDB_ORG", "architecture_research")
    influxdb_bucket: str = os.getenv("INFLUXDB_BUCKET", "mingtang_data")

    mqtt_broker: str = os.getenv("MQTT_BROKER", "localhost")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_username: Optional[str] = os.getenv("MQTT_USERNAME", None)
    mqtt_password: Optional[str] = os.getenv("MQTT_PASSWORD", None)
    mqtt_topic: str = os.getenv("MQTT_TOPIC", "mingtang/alerts")

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


shared_settings = SharedSettings()
