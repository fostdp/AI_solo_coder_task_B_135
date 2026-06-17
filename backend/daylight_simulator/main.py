#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""日光仿真微服务主入口 - 端口8002"""

import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import shared_settings, load_json_config
from shared.database import get_db_manager
from shared.redis_client import get_redis_client
from .simulation.sky_model import SkyModel, PerezSkyModel, CIEClearSky, CIEOvercastSky
from .simulation.ray_tracer import RayTracer, Ray, Intersection
from .simulation.lighting_calc import LightingCalculator, IlluminanceResult
from .services.simulation_service import get_simulation_service
from .api.simulation import router as simulation_router
from .api.features import router as features_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("日光仿真微服务启动中...")

    try:
        db_manager = get_db_manager()
        logger.info("InfluxDB连接已初始化")
    except Exception as e:
        logger.warning(f"InfluxDB初始化警告: {e}")

    try:
        redis_client = get_redis_client()
        logger.info("Redis连接已初始化")
    except Exception as e:
        logger.warning(f"Redis初始化警告: {e}")

    try:
        sky_config = load_json_config("sky_model_params.json")
        optical_config = load_json_config("optical_params.json")
        logger.info("JSON配置文件已加载")
    except Exception as e:
        logger.warning(f"配置文件加载警告: {e}")

    yield

    logger.info("日光仿真微服务关闭中...")

    try:
        db_manager = get_db_manager()
        db_manager.close()
        logger.info("InfluxDB连接已关闭")
    except Exception as e:
        logger.warning(f"InfluxDB关闭警告: {e}")

    try:
        redis_client = get_redis_client()
        redis_client.close()
        logger.info("Redis连接已关闭")
    except Exception as e:
        logger.warning(f"Redis关闭警告: {e}")

    logger.info("微服务关闭完成")


app = FastAPI(
    title="日光仿真微服务",
    description=(
        "汉长安明堂遗址采光仿真微服务。"
        "基于光线追踪和天空模型的照度分布计算，支持Perez/CIE天空模型。"
    ),
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

app.include_router(simulation_router, prefix="/api")
app.include_router(features_router, prefix="/api")


@app.get("/", tags=["系统"])
async def root():
    return {
        "name": "日光仿真微服务",
        "version": "1.0.0",
        "status": "running",
        "description": "汉长安明堂采光仿真微服务",
        "port": 8002,
        "api_docs": "/docs",
        "endpoints": {
            "run": "/api/simulation/run",
            "status": "/api/simulation/status/{task_id}",
            "tasks": "/api/simulation/tasks",
            "cancel": "/api/simulation/cancel/{task_id}",
            "result": "/api/simulation/result/{task_id}",
            "dynasty_comparison": "/api/features/dynasty-comparison/run",
            "standards_comparison": "/api/features/standards-comparison",
            "tree_impact": "/api/features/tree-impact/run",
            "virtual_tour": "/api/features/virtual-tour/run",
        }
    }


@app.get("/health", tags=["系统"])
async def health_check():
    db_status = "connected"
    redis_status = "connected"
    try:
        db_manager = get_db_manager()
        if not db_manager.client:
            db_status = "disconnected"
    except Exception:
        db_status = "disconnected"
    try:
        redis_client = get_redis_client()
        if redis_client.client is None:
            redis_status = "disconnected"
    except Exception:
        redis_status = "disconnected"
    return {
        "status": "healthy",
        "service": "daylight_simulator",
        "port": 8002,
        "services": {
            "influxdb": db_status,
            "redis": redis_status
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"未处理异常: {exc}", exc_info=True)
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
        "daylight_simulator.main:app",
        host="0.0.0.0",
        port=8002,
        reload=shared_settings.app_env == "development",
        log_level="info"
    )
