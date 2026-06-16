#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import APIRouter

from .sensor import router as sensor_router
from .simulation import router as simulation_router
from .optimization import router as optimization_router
from .alert import router as alert_router

api_router = APIRouter(prefix="/api")

api_router.include_router(sensor_router)
api_router.include_router(simulation_router)
api_router.include_router(optimization_router)
api_router.include_router(alert_router)
