import json
import logging
from typing import Optional

import redis

from .config import shared_settings

logger = logging.getLogger(__name__)


class RedisClient:
    _instance: Optional["RedisClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        self.client = redis.Redis(
            host=shared_settings.redis_host,
            port=shared_settings.redis_port,
            db=shared_settings.redis_db,
            password=shared_settings.redis_password,
            decode_responses=True,
        )
        try:
            self.client.ping()
            logger.info("Redis connected")
        except redis.ConnectionError:
            logger.warning("Redis not available, pub/sub disabled")
            self.client = None

    def publish(self, channel: str, message: dict) -> bool:
        if self.client is None:
            logger.warning(f"Redis not available, cannot publish to {channel}")
            return False
        try:
            self.client.publish(channel, json.dumps(message, ensure_ascii=False, default=str))
            logger.debug(f"Published to {channel}")
            return True
        except Exception as e:
            logger.error(f"Redis publish error: {e}")
            return False

    def subscribe(self, *channels: str):
        if self.client is None:
            logger.warning("Redis not available, cannot subscribe")
            return None
        try:
            pubsub = self.client.pubsub()
            pubsub.subscribe(*channels)
            logger.info(f"Subscribed to {channels}")
            return pubsub
        except Exception as e:
            logger.error(f"Redis subscribe error: {e}")
            return None

    def close(self):
        if self.client:
            self.client.close()


def get_redis_client() -> RedisClient:
    return RedisClient()
