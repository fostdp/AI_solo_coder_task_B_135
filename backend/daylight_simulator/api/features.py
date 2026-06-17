#!/usr/bin/env python3

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List

from shared.schemas import (
    DynastyComparisonParams,
    DynastyType,
    TreeImpactParams,
    VirtualTourParams,
    APIResponse
)
from ..services.feature_service import FeatureService, get_feature_service

router = APIRouter(prefix="/features", tags=["新功能扩展"])


@router.post("/dynasty-comparison/run")
async def run_dynasty_comparison(
    params: DynastyComparisonParams,
    service: FeatureService = Depends(get_feature_service)
):
    result = service.compare_dynasties(params)
    return APIResponse(status="success", message="朝代对比任务已启动", data=result)


@router.get("/dynasty-comparison/status/{task_id}")
async def get_dynasty_comparison_status(
    task_id: str,
    service: FeatureService = Depends(get_feature_service)
):
    result = service.get_task_status(task_id)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["error"])
    return APIResponse(status="success", data=result)


@router.get("/dynasty-config/{dynasty_key}")
async def get_dynasty_config(dynasty_key: str):
    from shared.config import load_json_config
    dynasty_params = load_json_config("dynasty_params.json")
    dynasties = dynasty_params.get("dynasties", {})
    if dynasty_key not in dynasties:
        raise HTTPException(status_code=404, detail=f"Dynasty {dynasty_key} not found")
    return APIResponse(status="success", data=dynasties[dynasty_key])


@router.get("/dynasty-list")
async def get_dynasty_list():
    from shared.config import load_json_config
    dynasty_params = load_json_config("dynasty_params.json")
    dynasties = dynasty_params.get("dynasties", {})
    result = []
    for key, val in dynasties.items():
        result.append({
            "key": key,
            "name": val.get("name", key),
            "year": val.get("year", ""),
            "description": val.get("description", ""),
            "color_scheme": val.get("color_scheme", {})
        })
    return APIResponse(status="success", data=result)


@router.get("/standards-comparison")
async def compare_standards(
    dynasty: DynastyType = Query(DynastyType.HAN),
    avg_illuminance: float = Query(300, ge=0),
    min_illuminance: float = Query(50, ge=0),
    uniformity: float = Query(0.5, ge=0, le=1),
    service: FeatureService = Depends(get_feature_service)
):
    result = service.compare_standards(
        dynasty_key=dynasty.value,
        avg_illuminance=avg_illuminance,
        min_illuminance=min_illuminance,
        uniformity=uniformity
    )
    return APIResponse(status="success", data=result)


@router.get("/standards-list")
async def get_standards_list():
    from shared.config import load_json_config
    standards_params = load_json_config("standards_params.json")
    standards = standards_params.get("modern_standards", {})
    result = []
    for key, val in standards.items():
        result.append({
            "key": key,
            "name": val.get("name", key),
            "country": val.get("country", ""),
            "year": val.get("year", 0)
        })
    return APIResponse(status="success", data=result)


@router.post("/tree-impact/run")
async def run_tree_impact(
    params: TreeImpactParams,
    service: FeatureService = Depends(get_feature_service)
):
    result = service.simulate_tree_impact(params)
    return APIResponse(status="success", message="树木影响仿真已启动", data=result)


@router.get("/tree-impact/status/{task_id}")
async def get_tree_impact_status(
    task_id: str,
    service: FeatureService = Depends(get_feature_service)
):
    result = service.get_task_status(task_id)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["error"])
    return APIResponse(status="success", data=result)


@router.get("/tree-species")
async def get_tree_species():
    from shared.config import load_json_config
    tree_params = load_json_config("tree_params.json")
    species = tree_params.get("tree_species", {})
    result = []
    for key, val in species.items():
        result.append({
            "key": key,
            "name": val.get("name", key),
            "trunk_radius": val.get("trunk_radius", 0.3),
            "canopy_radius": val.get("canopy_radius", 3.5),
            "canopy_transmittance": val.get("canopy_transmittance", 0.35)
        })
    return APIResponse(status="success", data=result)


@router.post("/virtual-tour/run")
async def run_virtual_tour(
    params: VirtualTourParams,
    service: FeatureService = Depends(get_feature_service)
):
    result = service.virtual_tour(params)
    return APIResponse(status="success", message="虚拟参观仿真已启动", data=result)


@router.get("/virtual-tour/status/{task_id}")
async def get_virtual_tour_status(
    task_id: str,
    service: FeatureService = Depends(get_feature_service)
):
    result = service.get_task_status(task_id)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result["error"])
    return APIResponse(status="success", data=result)
