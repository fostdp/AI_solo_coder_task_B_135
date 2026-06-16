#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.schemas import SensorDataBatch, SensorDataQuery, APIResponse
from ..services.sensor_service import SensorService, get_sensor_service

router = APIRouter(prefix="/sensor", tags=["传感器数据"])


@router.post("/data", response_model=APIResponse)
async def ingest_sensor_data(
    data_batch: SensorDataBatch,
    service: SensorService = Depends(get_sensor_service),
):
    """接收DTU传感器数据批次，写入InfluxDB并发布到Redis"""
    result = service.ingest_sensor_data(data_batch)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return APIResponse(
        status="success",
        message=result["message"],
        data={"count": result.get("count", 0)},
    )


@router.get("/data", response_model=APIResponse)
async def get_sensor_data(
    hall_id: str = Query("han_changan_mingtang", description="明堂ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    location: Optional[str] = Query(None, description="传感器位置"),
    service: SensorService = Depends(get_sensor_service),
):
    """从InfluxDB查询传感器历史数据"""
    data = service.get_sensor_data(
        hall_id=hall_id,
        start_time=start_time,
        end_time=end_time,
        location=location,
    )
    return APIResponse(
        status="success",
        message=f"查询到 {len(data)} 条传感器数据记录",
        data=data,
    )


@router.get("/latest", response_model=APIResponse)
async def get_latest_sensor_data(
    hall_id: str = Query("han_changan_mingtang", description="明堂ID"),
    location: Optional[str] = Query(None, description="传感器位置"),
    service: SensorService = Depends(get_sensor_service),
):
    """获取最新传感器数据（最近2小时内按时间戳最大值）"""
    result = service.get_latest_sensor_data(hall_id=hall_id, location=location)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    return APIResponse(
        status="success",
        message="获取最新传感器数据成功",
        data=result["data"],
    )


@router.get("/statistics", response_model=APIResponse)
async def get_sensor_statistics(
    hall_id: str = Query("han_changan_mingtang", description="明堂ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    service: SensorService = Depends(get_sensor_service),
):
    """计算照度统计信息（最大值、最小值、平均值）"""
    result = service.get_sensor_statistics(
        hall_id=hall_id,
        start_time=start_time,
        end_time=end_time,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return APIResponse(
        status="success",
        message="传感器统计信息计算完成",
        data=result["statistics"],
    )


@router.get("/sunshine-hours", response_model=APIResponse)
async def get_daily_sunshine_hours(
    hall_id: str = Query("han_changan_mingtang", description="明堂ID"),
    date: Optional[datetime] = Query(None, description="查询日期"),
    service: SensorService = Depends(get_sensor_service),
):
    """计算每日日照时长"""
    result = service.get_daily_sunshine_hours(hall_id=hall_id, date=date)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return APIResponse(
        status="success",
        message="日照时长计算完成",
        data={
            "date": result["date"],
            "sunshine_hours": result["sunshine_hours"],
            "hall_id": result["hall_id"],
        },
    )
