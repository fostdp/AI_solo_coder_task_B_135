#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import shared_settings
from shared.database import get_db_manager
from shared.redis_client import get_redis_client
from shared.schemas import RedisChannels
from .api.sensor import router as sensor_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库和Redis连接，关闭时释放资源"""
    logger.info("启动DTU数据接收微服务...")

    try:
        db_manager = get_db_manager()
        logger.info("数据库连接已初始化")
    except Exception as e:
        logger.warning(f"数据库初始化警告: {e}")

    try:
        redis_client = get_redis_client()
        logger.info("Redis连接已初始化")
    except Exception as e:
        logger.warning(f"Redis初始化警告: {e}")

    yield

    logger.info("关闭DTU数据接收微服务...")

    try:
        db_manager = get_db_manager()
        db_manager.close()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.warning(f"数据库关闭错误: {e}")

    try:
        redis_client = get_redis_client()
        redis_client.close()
        logger.info("Redis连接已关闭")
    except Exception as e:
        logger.warning(f"Redis关闭错误: {e}")

    logger.info("微服务关闭完成")


app = FastAPI(
    title="DTU数据接收微服务",
    description="明堂采光仿真系统 - 传感器数据采集、验证与Redis发布服务",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=shared_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sensor_router, prefix="/api")


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查端点"""
    db_manager = get_db_manager()
    redis_client = get_redis_client()
    return {
        "status": "healthy",
        "service": "dtu_receiver",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "services": {
            "influxdb": "connected" if db_manager.client else "disconnected",
            "redis": "connected" if redis_client.client else "disconnected",
        },
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"内部服务器错误: {str(exc)}",
            "detail": str(exc) if shared_settings.app_env == "development" else None,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "dtu_receiver.main:app",
        host="0.0.0.0",
        port=8001,
        reload=shared_settings.app_env == "development",
        log_level="info",
    )
