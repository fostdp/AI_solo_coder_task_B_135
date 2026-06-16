#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .core.config import settings
from .core.database import get_db_manager
from .api.router import api_router
from .services.alert_service import get_alert_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Mingtang Lighting Simulation System...")

    try:
        db_manager = get_db_manager()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")

    try:
        alert_service = get_alert_service()
        if alert_service.connect():
            logger.info("MQTT alert service connected")
        else:
            logger.warning("MQTT alert service failed to connect - will retry on demand")
    except Exception as e:
        logger.warning(f"MQTT service initialization warning: {e}")

    yield

    logger.info("Shutting down Mingtang Lighting Simulation System...")

    try:
        alert_service = get_alert_service()
        alert_service.disconnect()
        logger.info("MQTT alert service disconnected")
    except Exception as e:
        logger.warning(f"Error during MQTT shutdown: {e}")

    try:
        db_manager = get_db_manager()
        db_manager.close()
        logger.info("Database connection closed")
    except Exception as e:
        logger.warning(f"Error during database shutdown: {e}")

    logger.info("Shutdown completed")


app = FastAPI(
    title="古代明堂建筑采光仿真与日照优化系统",
    description=(
        "汉长安明堂遗址采光性能数字化复原研究系统。"
        "集成光线追踪仿真、粒子群优化算法、实时传感器数据采集和MQTT告警推送。"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["系统"])
async def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "description": "古代明堂建筑采光仿真与日照优化系统",
        "api_docs": "/docs",
        "endpoints": {
            "sensor": "/api/sensor",
            "simulation": "/api/simulation",
            "optimization": "/api/optimization",
            "alert": "/api/alert"
        }
    }


@app.get("/health", tags=["系统"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": "now",
        "services": {
            "influxdb": "connected" if get_db_manager().client else "disconnected",
            "mqtt": "connected" if get_alert_service()._connected else "disconnected"
        }
    }


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="古代明堂建筑采光仿真与日照优化系统 API",
        version="1.0.0",
        description=(
            "本API提供汉长安明堂遗址采光性能研究的完整接口，包括：\n\n"
            "- **传感器数据**：实时数据采集、历史查询、统计分析\n"
            "- **采光仿真**：基于光线追踪和天空模型的照度分布计算\n"
            "- **日照优化**：粒子群算法优化窗户参数，提升采光均匀度\n"
            "- **告警管理**：冬季日照不足预警，MQTT消息推送\n"
        ),
        routes=app.routes,
    )

    openapi_schema["info"]["x-logo"] = {
        "url": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Cpolygon points='50,10 90,40 75,90 25,90 10,40' fill='%238B4513'/%3E%3C/svg%3E"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"Internal server error: {str(exc)}",
            "detail": str(exc) if settings.app_env == "development" else None
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level="info"
    )
