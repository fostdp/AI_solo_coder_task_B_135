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

from shared.config import shared_settings, load_json_config
from shared.database import get_db_manager
from shared.redis_client import get_redis_client
from shared.schemas import RedisChannels, TaskStatus

from .optimization.pso_optimizer import ParticleSwarmOptimizer, LightingFitnessEvaluator, WindowParameters
from .services.optimization_service import OptimizationService
from .api.optimization import router as optimization_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Sunlight Optimizer Service...")

    try:
        db_manager = get_db_manager()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")

    try:
        redis_client = get_redis_client()
        logger.info("Redis client initialized")
    except Exception as e:
        logger.warning(f"Redis initialization warning: {e}")

    yield

    logger.info("Shutting down Sunlight Optimizer Service...")

    try:
        db_manager = get_db_manager()
        db_manager.close()
        logger.info("Database connection closed")
    except Exception as e:
        logger.warning(f"Error during database shutdown: {e}")

    try:
        redis_client = get_redis_client()
        redis_client.close()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.warning(f"Error during Redis shutdown: {e}")

    logger.info("Shutdown completed")


app = FastAPI(
    title="Sunlight Optimizer Service",
    description="PSO particle swarm optimization microservice for window placement in the Mingtang lighting simulation system.",
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

app.include_router(optimization_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Sunlight Optimizer Service",
        "version": "1.0.0",
        "status": "running",
        "description": "PSO optimization microservice for Mingtang lighting simulation",
        "api_docs": "/docs",
        "endpoints": {
            "optimization": "/api/optimization"
        }
    }


@app.get("/health")
async def health_check():
    db_connected = False
    redis_connected = False
    try:
        db_manager = get_db_manager()
        db_connected = db_manager.client is not None
    except Exception:
        pass
    try:
        redis_client = get_redis_client()
        redis_connected = redis_client.client is not None
    except Exception:
        pass
    return {
        "status": "healthy",
        "timestamp": "now",
        "services": {
            "influxdb": "connected" if db_connected else "disconnected",
            "redis": "connected" if redis_connected else "disconnected"
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
        "sunlight_optimizer.main:app",
        host="0.0.0.0",
        port=8003,
        reload=shared_settings.app_env == "development",
        log_level="info"
    )
