#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from ..core.database import get_db_manager, InfluxDBManager
from ..models.schemas import (
    SimulationParams,
    SimulationResultData,
    TaskStatus
)
from simulation import (
    BuildingGeometry,
    LightingCalculator
)

logger = logging.getLogger(__name__)


class SimulationService:
    def __init__(self):
        self.db_manager: InfluxDBManager = get_db_manager()
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def create_simulation_task(self, params: SimulationParams) -> Dict[str, Any]:
        task_id = f"sim_{uuid.uuid4().hex[:12]}"

        task_info = {
            "task_id": task_id,
            "status": TaskStatus.PENDING.value,
            "params": params,
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": datetime.now()
        }

        self.tasks[task_id] = task_info

        asyncio.create_task(self._run_simulation(task_id, params))

        return {
            "task_id": task_id,
            "status": TaskStatus.RUNNING.value,
            "message": "Simulation task started"
        }

    async def _run_simulation(self, task_id: str, params: SimulationParams):
        try:
            self.tasks[task_id]["status"] = TaskStatus.RUNNING.value
            logger.info(f"Starting simulation task {task_id}")

            building = BuildingGeometry()
            calculator = LightingCalculator(
                building=building,
                latitude=params.latitude,
                longitude=params.longitude,
                grid_resolution=params.grid_resolution
            )

            date_obj = datetime.strptime(params.date, "%Y-%m-%d")
            results = []

            total_steps = max(1, (params.end_hour - params.start_hour) * 60 // params.time_step)
            current_step = 0

            current_time = datetime(
                date_obj.year, date_obj.month, date_obj.day,
                params.start_hour
            )
            end_time = datetime(
                date_obj.year, date_obj.month, date_obj.day,
                params.end_hour
            )

            while current_time <= end_time:
                result = calculator.calculate_illuminance(
                    current_time,
                    sky_model_type=params.sky_model.value,
                    turbidity=params.turbidity
                )

                results.append(SimulationResultData(**result.to_dict()))

                result_record = {
                    "hall_id": params.hall_id,
                    "sky_model": params.sky_model.value,
                    "max_illuminance": result.max_illuminance,
                    "min_illuminance": result.min_illuminance,
                    "avg_illuminance": result.avg_illuminance,
                    "uniformity": result.uniformity,
                    "grid_resolution": params.grid_resolution,
                    "timestamp": result.timestamp
                }
                self.db_manager.write_simulation_result(task_id, result_record)

                current_step += 1
                self.tasks[task_id]["progress"] = min(current_step / total_steps, 1.0)

                current_time += timedelta(minutes=params.time_step)
                await asyncio.sleep(0.1)

            self.tasks[task_id]["status"] = TaskStatus.COMPLETED.value
            self.tasks[task_id]["progress"] = 1.0
            self.tasks[task_id]["result"] = [r.model_dump() for r in results]

            logger.info(f"Simulation task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Simulation task {task_id} failed: {e}")
            self.tasks[task_id]["status"] = TaskStatus.FAILED.value
            self.tasks[task_id]["error"] = str(e)

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        task = self.tasks.get(task_id)

        if task is None:
            return {
                "task_id": task_id,
                "status": "not_found",
                "error": f"Task {task_id} not found"
            }

        return {
            "task_id": task_id,
            "status": task["status"],
            "progress": task["progress"],
            "result": task["result"],
            "error": task["error"]
        }

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        return [
            {
                "task_id": tid,
                "status": t["status"],
                "progress": t["progress"],
                "created_at": t["created_at"].isoformat()
            }
            for tid, t in self.tasks.items()
        ]

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        task = self.tasks.get(task_id)

        if task is None:
            return {
                "task_id": task_id,
                "status": "not_found",
                "message": f"Task {task_id} not found"
            }

        if task["status"] in [TaskStatus.RUNNING.value, TaskStatus.PENDING.value]:
            task["status"] = TaskStatus.FAILED.value
            task["error"] = "Task cancelled by user"
            return {
                "task_id": task_id,
                "status": "cancelled",
                "message": f"Task {task_id} has been cancelled"
            }
        else:
            return {
                "task_id": task_id,
                "status": task["status"],
                "message": f"Task {task_id} is already {task['status']}"
            }


def get_simulation_service() -> SimulationService:
    return SimulationService()
