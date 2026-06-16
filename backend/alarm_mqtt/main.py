#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import shared_settings
from shared.schemas import RedisChannels
from .services.alert_service import MQTTAlertService, get_alert_service
from .api.alert import router as alert_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

_alert_service: MQTTAlertService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _alert_service

    logger.info("Starting Alarm MQTT Service...")

    _alert_service = get_alert_service()

    try:
        if _alert_service.connect():
            logger.info("MQTT alert service connected")
        else:
            logger.warning("MQTT alert service failed to connect - will retry on demand")
    except Exception as e:
        logger.warning(f"MQTT service initialization warning: {e}")

    try:
        _alert_service.start_redis_subscriber()
        logger.info(f"Redis subscriber started on channel: {RedisChannels.SENSOR_DATA}")
    except Exception as e:
        logger.warning(f"Redis subscriber initialization warning: {e}")

    yield

    logger.info("Shutting down Alarm MQTT Service...")

    try:
        _alert_service.stop_redis_subscriber()
        logger.info("Redis subscriber stopped")
    except Exception as e:
        logger.warning(f"Error stopping Redis subscriber: {e}")

    try:
        _alert_service.disconnect()
        logger.info("MQTT alert service disconnected")
    except Exception as e:
        logger.warning(f"Error during MQTT shutdown: {e}")

    logger.info("Shutdown completed")


app = FastAPI(
    title="明堂告警MQTT推送服务",
    description="汉长安明堂遗址日照不足预警与MQTT消息推送微服务，集成Redis传感器数据订阅。",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=shared_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alert_router, prefix="/api")


@app.get("/health")
async def health_check():
    service = _alert_service or get_alert_service()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "alarm_mqtt",
        "services": {
            "influxdb": "connected" if service.db_manager.client else "disconnected",
            "mqtt": "connected" if service._connected else "disconnected",
            "redis_subscriber": "running" if (service._subscriber_thread and service._subscriber_thread.is_alive()) else "stopped"
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"Internal server error: {str(exc)}",
            "detail": str(exc) if shared_settings.app_env == "development" else None
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "alarm_mqtt.main:app",
        host="0.0.0.0",
        port=8004,
        reload=shared_settings.app_env == "development",
        log_level="info"
    )
