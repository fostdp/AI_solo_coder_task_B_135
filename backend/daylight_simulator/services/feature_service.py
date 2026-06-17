#!/usr/bin/env python3
import logging
import uuid
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from shared.database import get_db_manager, InfluxDBManager
from shared.redis_client import get_redis_client, RedisClient
from shared.schemas import (
    DynastyComparisonParams, DynastySimulationResult,
    StandardsComparisonResult,
    TreeImpactParams, TreeImpactResult,
    VirtualTourParams, VirtualTourResult, VirtualTourHourData,
    TaskStatus, RedisChannels
)
from ..simulation.lighting_calc import BuildingGeometry, LightingCalculator
from shared.config import load_json_config

logger = logging.getLogger(__name__)


class FeatureService:
    def __init__(self):
        self.db_manager: InfluxDBManager = get_db_manager()
        self.redis_client: RedisClient = get_redis_client()
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def _create_task(self, task_type: str) -> str:
        task_id = f"{task_type}_{uuid.uuid4().hex[:12]}"
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": datetime.now()
        }
        return task_id

    def compare_dynasties(self, params: DynastyComparisonParams) -> Dict[str, Any]:
        task_id = self._create_task("dynasty_cmp")
        asyncio.create_task(self._run_dynasty_comparison(task_id, params))
        return {"task_id": task_id, "status": TaskStatus.RUNNING.value}

    async def _run_dynasty_comparison(self, task_id: str, params: DynastyComparisonParams):
        try:
            self.tasks[task_id]["status"] = TaskStatus.RUNNING.value
            dynasty_params = load_json_config("dynasty_params.json")
            dynasties_db = dynasty_params.get("dynasties", {})
            results = []
            total = len(params.dynasties)

            for i, dynasty_enum in enumerate(params.dynasties):
                dynasty_key = dynasty_enum.value
                dynasty_data = dynasties_db.get(dynasty_key, dynasties_db.get("han", {}))

                calculator = LightingCalculator.from_dynasty(dynasty_key, params.grid_resolution)
                dt = datetime.strptime(params.date, "%Y-%m-%d").replace(hour=params.hour)

                result = calculator.calculate_illuminance(
                    dt,
                    sky_model_type=params.sky_model.value,
                    turbidity=params.turbidity
                )

                building_cfg = dynasty_data.get("building", {})
                results.append(DynastySimulationResult(
                    dynasty=dynasty_key,
                    dynasty_name=dynasty_data.get("name", dynasty_key),
                    year=dynasty_data.get("year", ""),
                    avg_illuminance=float(result.avg_illuminance),
                    min_illuminance=float(result.min_illuminance),
                    max_illuminance=float(result.max_illuminance),
                    uniformity=float(result.uniformity),
                    grid_size={"x": result.grid_size[0], "y": result.grid_size[1], "z": result.grid_size[2]},
                    illuminance_matrix=result.illuminance_matrix.tolist(),
                    solar_altitude=float(result.solar_altitude),
                    solar_azimuth=float(result.solar_azimuth),
                    building_specs={
                        "length": building_cfg.get("length", 20),
                        "width": building_cfg.get("width", 20),
                        "height": building_cfg.get("height", 12),
                        "windows_count": len(building_cfg.get("default_windows", [])),
                        "window_transmittance": building_cfg.get("default_windows", [{}])[0].get("transmittance", 0.7) if building_cfg.get("default_windows") else 0.7
                    }
                ))

                self.tasks[task_id]["progress"] = (i + 1) / total
                await asyncio.sleep(0.05)

            self.tasks[task_id]["status"] = TaskStatus.COMPLETED.value
            self.tasks[task_id]["progress"] = 1.0
            self.tasks[task_id]["result"] = [r.model_dump() for r in results]

        except Exception as e:
            logger.error(f"朝代对比任务失败 {task_id}: {e}")
            self.tasks[task_id]["status"] = TaskStatus.FAILED.value
            self.tasks[task_id]["error"] = str(e)

    def compare_standards(self, dynasty_key: str, avg_illuminance: float,
                          min_illuminance: float, uniformity: float) -> List[Dict[str, Any]]:
        standards_params = load_json_config("standards_params.json")
        standards_db = standards_params.get("modern_standards", {})
        categories = standards_params.get("comparison_categories", [])
        dynasty_params = load_json_config("dynasty_params.json")
        dynasty_data = dynasty_params.get("dynasties", {}).get(dynasty_key, {})

        df_min = (min_illuminance / 10000.0) * 100
        df_avg = (avg_illuminance / 10000.0) * 100

        simulated = {
            "daylight_factor_min": round(df_min, 2),
            "daylight_factor_avg": round(df_avg, 2),
            "illuminance_min": round(min_illuminance, 1),
            "illuminance_avg": round(avg_illuminance, 1),
            "uniformity_min": round(uniformity, 3),
            "dgp_max": 0.35,
            "da300": round(min(100, avg_illuminance / 5), 1),
            "udi_100_3000": round(min(100, (1 - abs(avg_illuminance - 1500) / 3000) * 100), 1)
        }

        results = []
        for std_key, std_data in standards_db.items():
            compliance = {}
            total_score = 0.0
            total_weight = 0.0

            for cat in categories:
                cat_key = cat["key"]
                weight = cat["weight"]
                std_value = std_data.get("metrics", {}).get(cat_key, {}).get("value", 0)
                sim_value = simulated.get(cat_key, 0)

                if std_value > 0:
                    ratio = min(sim_value / std_value, 1.5)
                    score = min(1.0, ratio)
                    compliance[cat_key] = {
                        "standard_value": std_value,
                        "simulated_value": round(sim_value, 2),
                        "compliance_ratio": round(ratio, 3),
                        "pass": sim_value >= std_value
                    }
                    total_score += score * weight
                    total_weight += weight

            overall = total_score / total_weight if total_weight > 0 else 0

            results.append({
                "standard_key": std_key,
                "standard_name": std_data.get("name", std_key),
                "country": std_data.get("country", ""),
                "year": std_data.get("year", 0),
                "dynasty": dynasty_key,
                "dynasty_name": dynasty_data.get("name", dynasty_key),
                "simulated_metrics": simulated,
                "standards_compliance": compliance,
                "overall_score": round(overall, 3)
            })

        return results

    def simulate_tree_impact(self, params: TreeImpactParams) -> Dict[str, Any]:
        task_id = self._create_task("tree_impact")
        asyncio.create_task(self._run_tree_impact(task_id, params))
        return {"task_id": task_id, "status": TaskStatus.RUNNING.value}

    async def _run_tree_impact(self, task_id: str, params: TreeImpactParams):
        try:
            self.tasks[task_id]["status"] = TaskStatus.RUNNING.value
            dynasty_key = params.dynasty.value

            calculator = LightingCalculator.from_dynasty(dynasty_key, params.grid_resolution)
            dt = datetime.strptime(params.date, "%Y-%m-%d").replace(hour=params.hour)

            result_without = calculator.calculate_illuminance(
                dt, sky_model_type=params.sky_model.value, turbidity=params.turbidity
            )

            without_data = {
                "avg_illuminance": float(result_without.avg_illuminance),
                "min_illuminance": float(result_without.min_illuminance),
                "max_illuminance": float(result_without.max_illuminance),
                "uniformity": float(result_without.uniformity),
                "illuminance_matrix": result_without.illuminance_matrix.tolist()
            }

            self.tasks[task_id]["progress"] = 0.5

            tree_params_cfg = load_json_config("tree_params.json")
            trees_to_add = []
            if params.trees:
                trees_to_add = [t.model_dump() for t in params.trees]
            else:
                default_layout = tree_params_cfg.get("default_layout", {})
                trees_to_add = default_layout.get("trees", [])

            calculator.add_trees(trees_to_add, params.season)

            result_with = calculator.calculate_illuminance(
                dt, sky_model_type=params.sky_model.value, turbidity=params.turbidity
            )

            with_data = {
                "avg_illuminance": float(result_with.avg_illuminance),
                "min_illuminance": float(result_with.min_illuminance),
                "max_illuminance": float(result_with.max_illuminance),
                "uniformity": float(result_with.uniformity),
                "illuminance_matrix": result_with.illuminance_matrix.tolist()
            }

            reduction = 0.0
            if result_without.avg_illuminance > 0:
                reduction = (1 - result_with.avg_illuminance / result_without.avg_illuminance) * 100

            uniformity_change = result_with.uniformity - result_without.uniformity

            diff_matrix = result_without.illuminance_matrix - result_with.illuminance_matrix
            shaded_pct = float(np.sum(diff_matrix > 10) / diff_matrix.size * 100) if diff_matrix.size > 0 else 0

            species_db = tree_params_cfg.get("tree_species", {})
            tree_details = []
            for t_cfg in trees_to_add:
                sp = species_db.get(t_cfg.get("species", "pine"), {})
                tree_details.append({
                    "species": t_cfg.get("species", "pine"),
                    "species_name": sp.get("name", t_cfg.get("species", "pine")),
                    "position": t_cfg.get("position", [0, 0, 0]),
                    "canopy_radius": sp.get("canopy_radius", 3.5) * t_cfg.get("scale", 1.0),
                    "canopy_height": sp.get("canopy_height", 4.0) * t_cfg.get("scale", 1.0),
                    "transmittance": sp.get("canopy_transmittance", 0.35)
                })

            impact = TreeImpactResult(
                without_trees=without_data,
                with_trees=with_data,
                illuminance_reduction_pct=round(reduction, 2),
                uniformity_change=round(uniformity_change, 4),
                shaded_area_pct=round(shaded_pct, 1),
                tree_details=tree_details
            )

            self.tasks[task_id]["status"] = TaskStatus.COMPLETED.value
            self.tasks[task_id]["progress"] = 1.0
            self.tasks[task_id]["result"] = impact.model_dump()

        except Exception as e:
            logger.error(f"树木影响仿真失败 {task_id}: {e}")
            self.tasks[task_id]["status"] = TaskStatus.FAILED.value
            self.tasks[task_id]["error"] = str(e)

    def virtual_tour(self, params: VirtualTourParams) -> Dict[str, Any]:
        task_id = self._create_task("vtour")
        asyncio.create_task(self._run_virtual_tour(task_id, params))
        return {"task_id": task_id, "status": TaskStatus.RUNNING.value}

    async def _run_virtual_tour(self, task_id: str, params: VirtualTourParams):
        try:
            self.tasks[task_id]["status"] = TaskStatus.RUNNING.value
            dynasty_key = params.dynasty.value
            dynasty_params = load_json_config("dynasty_params.json")
            dynasty_data = dynasty_params.get("dynasties", {}).get(dynasty_key, {})

            calculator = LightingCalculator.from_dynasty(dynasty_key, params.grid_resolution)
            date_obj = datetime.strptime(params.date, "%Y-%m-%d")

            hourly_data = []
            sun_path = []

            current = datetime(date_obj.year, date_obj.month, date_obj.day, params.start_hour)
            end_time = datetime(date_obj.year, date_obj.month, date_obj.day, params.end_hour)
            total_minutes = (params.end_hour - params.start_hour) * 60
            elapsed = 0

            while current <= end_time:
                result = calculator.calculate_illuminance(
                    current,
                    sky_model_type=params.sky_model.value,
                    turbidity=params.turbidity
                )

                hour_float = current.hour + current.minute / 60.0

                hourly_data.append(VirtualTourHourData(
                    hour=hour_float,
                    solar_altitude=float(result.solar_altitude),
                    solar_azimuth=float(result.solar_azimuth),
                    avg_illuminance=float(result.avg_illuminance),
                    min_illuminance=float(result.min_illuminance),
                    max_illuminance=float(result.max_illuminance),
                    uniformity=float(result.uniformity),
                    illuminance_matrix=result.illuminance_matrix.tolist()
                ))

                if result.solar_altitude > 0:
                    sun_path.append({
                        "hour": hour_float,
                        "altitude": float(result.solar_altitude),
                        "azimuth": float(result.solar_azimuth)
                    })

                elapsed += params.time_step
                self.tasks[task_id]["progress"] = min(elapsed / total_minutes, 1.0)
                current += timedelta(minutes=params.time_step)
                await asyncio.sleep(0.05)

            tour_result = VirtualTourResult(
                dynasty=dynasty_key,
                dynasty_name=dynasty_data.get("name", dynasty_key),
                date=params.date,
                latitude=calculator.latitude,
                longitude=calculator.longitude,
                hourly_data=hourly_data,
                sun_path=sun_path
            )

            self.tasks[task_id]["status"] = TaskStatus.COMPLETED.value
            self.tasks[task_id]["progress"] = 1.0
            self.tasks[task_id]["result"] = tour_result.model_dump()

        except Exception as e:
            logger.error(f"虚拟参观仿真失败 {task_id}: {e}")
            self.tasks[task_id]["status"] = TaskStatus.FAILED.value
            self.tasks[task_id]["error"] = str(e)

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        task = self.tasks.get(task_id)
        if task is None:
            return {"task_id": task_id, "status": "not_found", "error": f"Task {task_id} not found"}
        return {
            "task_id": task_id,
            "status": task["status"],
            "progress": task["progress"],
            "result": task["result"],
            "error": task["error"]
        }


_service_instance: Optional['FeatureService'] = None


def get_feature_service() -> FeatureService:
    global _service_instance
    if _service_instance is None:
        _service_instance = FeatureService()
    return _service_instance
