#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any

from shared.schemas import (
    OptimizationParams,
    OptimizationTaskResponse,
    OptimizationStatusResponse,
    APIResponse
)
from ..services.optimization_service import OptimizationService, get_optimization_service

router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.post("/run", response_model=OptimizationTaskResponse)
async def run_optimization(
    params: OptimizationParams,
    service: OptimizationService = Depends(get_optimization_service)
):
    result = service.create_optimization_task(params)
    return OptimizationTaskResponse(**result)


@router.get("/status/{task_id}", response_model=OptimizationStatusResponse)
async def get_optimization_status(
    task_id: str,
    service: OptimizationService = Depends(get_optimization_service)
):
    result = service.get_task_status(task_id)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["error"])
    return OptimizationStatusResponse(**result)


@router.get("/tasks", response_model=APIResponse)
async def get_all_optimization_tasks(
    service: OptimizationService = Depends(get_optimization_service)
):
    tasks = service.get_all_tasks()
    return APIResponse(
        status="success",
        message=f"Retrieved {len(tasks)} optimization tasks",
        data=tasks
    )


@router.post("/cancel/{task_id}", response_model=APIResponse)
async def cancel_optimization(
    task_id: str,
    service: OptimizationService = Depends(get_optimization_service)
):
    result = service.cancel_task(task_id)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["message"])
    return APIResponse(
        status="success",
        message=result["message"],
        data={"task_id": task_id, "status": result["status"]}
    )


@router.get("/result/{task_id}", response_model=APIResponse)
async def get_optimization_result(
    task_id: str,
    service: OptimizationService = Depends(get_optimization_service)
):
    result = service.get_task_status(task_id)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["error"])
    if result["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Optimization task is {result['status']}, not completed yet"
        )
    return APIResponse(
        status="success",
        message="Optimization result retrieved",
        data=result["result"]
    )


@router.post("/compare", response_model=APIResponse)
async def compare_solutions(
    original_windows: Optional[List[Dict]] = None,
    optimized_windows: Optional[List[Dict]] = None,
    service: OptimizationService = Depends(get_optimization_service)
):
    result = service.compare_solutions(original_windows, optimized_windows)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return APIResponse(
        status="success",
        message="Solution comparison completed",
        data=result
    )
