#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..models.schemas import (
    AlertConfig,
    AlertRecord,
    APIResponse
)
from ..services.alert_service import MQTTAlertService, get_alert_service

router = APIRouter(prefix="/alert", tags=["告警管理"])


@router.post("/check", response_model=APIResponse)
async def check_sunshine_alert(
    hall_id: str = Query("han_changan_mingtang", description="明堂ID"),
    service: MQTTAlertService = Depends(get_alert_service)
):
    alert = service.check_and_send_sunshine_alert(hall_id=hall_id)
    if alert:
        return APIResponse(
            status="success",
            message="Alert check completed - alert triggered",
            data={"alert_triggered": True, "alert": alert}
        )
    else:
        return APIResponse(
            status="success",
            message="Alert check completed - no alert needed",
            data={"alert_triggered": False}
        )


@router.post("/config", response_model=APIResponse)
async def update_alert_config(
    config: AlertConfig,
    service: MQTTAlertService = Depends(get_alert_service)
):
    service.default_topic = config.mqtt_topic
    return APIResponse(
        status="success",
        message="Alert configuration updated",
        data=config.model_dump()
    )


@router.get("/history", response_model=APIResponse)
async def get_alert_history(
    hall_id: Optional[str] = Query(None, description="明堂ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    service: MQTTAlertService = Depends(get_alert_service)
):
    alerts = service.get_alert_history(
        hall_id=hall_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    return APIResponse(
        status="success",
        message=f"Retrieved {len(alerts)} alert records",
        data=alerts
    )


@router.post("/test", response_model=APIResponse)
async def send_test_alert(
    hall_id: str = Query("han_changan_mingtang", description="明堂ID"),
    service: MQTTAlertService = Depends(get_alert_service)
):
    test_alert = {
        "alert_id": f"test_alert_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "hall_id": hall_id,
        "alert_type": "test",
        "timestamp": datetime.now(),
        "message": "【测试告警】这是一条测试告警消息，用于验证MQTT推送功能。",
        "sunshine_hours": 2.5,
        "threshold": 3.0,
        "acknowledged": False,
        "details": {
            "test": True,
            "description": "Manual test alert"
        }
    }

    success = service.publish_alert(test_alert)
    if success:
        service.db_manager.write_alert_record(test_alert)
        return APIResponse(
            status="success",
            message="Test alert sent successfully",
            data={"alert": test_alert}
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to send test alert - check MQTT connection"
        )
