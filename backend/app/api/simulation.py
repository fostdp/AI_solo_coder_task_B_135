#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any

from ..models.schemas import (
    SimulationParams,
    SimulationTaskResponse,
    SimulationStatusResponse,
    APIResponse
)
from ..services.simulation_service import SimulationService, get_simulation_service

router = APIRouter(prefix="/simulation", tags=["采光仿真"])


@router.post("/run", response_model=SimulationTaskResponse)
async def run_simulation(
    params: SimulationParams,
    service: SimulationService = Depends(get_simulation_service)
):
    result = service.create_simulation_task(params)
    return SimulationTaskResponse(**result)


@router.get("/status/{task_id}", response_model=SimulationStatusResponse)
async def get_simulation_status(
    task_id: str,
    service: SimulationService = Depends(get_simulation_service)
):
    result = service.get_task_status(task_id)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["error"])
    return SimulationStatusResponse(**result)


@router.get("/tasks", response_model=APIResponse)
async def get_all_simulation_tasks(
    service: SimulationService = Depends(get_simulation_service)
):
    tasks = service.get_all_tasks()
    return APIResponse(
        status="success",
        message=f"Retrieved {len(tasks)} simulation tasks",
        data=tasks
    )


@router.post("/cancel/{task_id}", response_model=APIResponse)
async def cancel_simulation(
    task_id: str,
    service: SimulationService = Depends(get_simulation_service)
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
async def get_simulation_result(
    task_id: str,
    service: SimulationService = Depends(get_simulation_service)
):
    result = service.get_task_status(task_id)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["error"])
    if result["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Simulation task is {result['status']}, not completed yet"
        )
    return APIResponse(
        status="success",
        message="Simulation result retrieved",
        data=result["result"]
    )
