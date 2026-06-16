#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..models.schemas import (
    SensorDataBatch,
    SensorDataPoint,
    APIResponse
)
from ..services.sensor_service import SensorService, get_sensor_service

router = APIRouter(prefix="/sensor", tags=["传感器数据"])


@router.post("/data", response_model=APIResponse)
async def ingest_sensor_data(
    data_batch: SensorDataBatch,
    service: SensorService = Depends(get_sensor_service)
):
    result = service.ingest_sensor_data(data_batch)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return APIResponse(
        status="success",
        message=result["message"],
        data={"count": result.get("count", 0)}
    )


@router.get("/data", response_model=APIResponse)
async def get_sensor_data(
    hall_id: str = Query("han_changan_mingtang", description="明堂ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    location: Optional[str] = Query(None, description="传感器位置"),
    service: SensorService = Depends(get_sensor_service)
):
    data = service.get_sensor_data(
        hall_id=hall_id,
        start_time=start_time,
        end_time=end_time,
        location=location
    )
    return APIResponse(
        status="success",
        message=f"Retrieved {len(data)} sensor data records",
        data=data
    )


@router.get("/latest", response_model=APIResponse)
async def get_latest_sensor_data(
    hall_id: str = Query("han_changan_mingtang", description="明堂ID"),
    location: Optional[str] = Query(None, description="传感器位置"),
    service: SensorService = Depends(get_sensor_service)
):
    result = service.get_latest_sensor_data(hall_id=hall_id, location=location)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    return APIResponse(
        status="success",
        message="Latest sensor data retrieved",
        data=result["data"]
    )


@router.get("/statistics", response_model=APIResponse)
async def get_sensor_statistics(
    hall_id: str = Query("han_changan_mingtang", description="明堂ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    service: SensorService = Depends(get_sensor_service)
):
    result = service.get_sensor_statistics(
        hall_id=hall_id,
        start_time=start_time,
        end_time=end_time
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return APIResponse(
        status="success",
        message="Sensor statistics calculated",
        data=result["statistics"]
    )


@router.get("/sunshine-hours", response_model=APIResponse)
async def get_daily_sunshine_hours(
    hall_id: str = Query("han_changan_mingtang", description="明堂ID"),
    date: Optional[datetime] = Query(None, description="查询日期"),
    service: SensorService = Depends(get_sensor_service)
):
    result = service.get_daily_sunshine_hours(hall_id=hall_id, date=date)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return APIResponse(
        status="success",
        message="Daily sunshine hours calculated",
        data={
            "date": result["date"],
            "sunshine_hours": result["sunshine_hours"],
            "hall_id": result["hall_id"]
        }
    )
