#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import uuid
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from ..core.database import get_db_manager, InfluxDBManager
from ..core.config import settings
from ..models.schemas import (
    OptimizationParams,
    OptimizationResultData,
    WindowSolution,
    TaskStatus
)
from simulation import (
    BuildingGeometry,
    LightingCalculator
)
from optimization import (
    ParticleSwarmOptimizer,
    LightingFitnessEvaluator,
    WindowParameters
)

logger = logging.getLogger(__name__)


class OptimizationService:
    def __init__(self):
        self.db_manager: InfluxDBManager = get_db_manager()
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def create_optimization_task(self, params: OptimizationParams) -> Dict[str, Any]:
        task_id = f"opt_{uuid.uuid4().hex[:12]}"

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

        asyncio.create_task(self._run_optimization(task_id, params))

        return {
            "task_id": task_id,
            "status": TaskStatus.RUNNING.value,
            "message": "Optimization task started"
        }

    async def _run_optimization(self, task_id: str, params: OptimizationParams):
        try:
            self.tasks[task_id]["status"] = TaskStatus.RUNNING.value
            logger.info(f"Starting optimization task {task_id}")

            building = BuildingGeometry()
            calculator = LightingCalculator(
                building=building,
                latitude=settings.latitude,
                longitude=settings.longitude,
                grid_resolution=10
            )

            position_min = np.array(params.window_params.position_range["min"], dtype=np.float64)
            position_max = np.array(params.window_params.position_range["max"], dtype=np.float64)
            size_min = np.array(params.window_params.size_range["min"], dtype=np.float64)
            size_max = np.array(params.window_params.size_range["max"], dtype=np.float64)

            evaluator = LightingFitnessEvaluator(
                lighting_calculator=calculator,
                target_uniformity_weight=0.6,
                avg_illuminance_weight=0.4,
                min_avg_illuminance=100.0
            )

            def progress_callback(iteration: int, best_fitness: float):
                progress = min(iteration / params.max_iterations, 1.0)
                self.tasks[task_id]["progress"] = progress
                logger.debug(f"Optimization {task_id}: iteration {iteration}, fitness {best_fitness:.4f}")

            optimizer = ParticleSwarmOptimizer(
                fitness_function=evaluator,
                num_windows=params.num_windows,
                population_size=params.population_size,
                max_iterations=params.max_iterations,
                w=0.7,
                c1=1.5,
                c2=1.5,
                position_bounds=(position_min, position_max),
                size_bounds=(size_min, size_max),
                random_seed=42
            )

            result = optimizer.optimize(callback=progress_callback)

            result_data = OptimizationResultData(
                best_solution=[
                    WindowSolution(
                        position=wp.position.tolist(),
                        size=wp.size.tolist(),
                        transmittance=float(wp.transmittance)
                    )
                    for wp in result.best_solution
                ],
                best_fitness=float(result.best_fitness),
                uniformity=float(result.uniformity),
                convergence_curve=[float(x) for x in result.convergence_curve],
                iterations=int(result.iterations),
                avg_illuminance=float(result.avg_illuminance),
                execution_time=float(result.execution_time)
            )

            self.tasks[task_id]["status"] = TaskStatus.COMPLETED.value
            self.tasks[task_id]["progress"] = 1.0
            self.tasks[task_id]["result"] = result_data.model_dump()

            result_record = {
                "hall_id": params.hall_id,
                "algorithm": "pso",
                "best_fitness": result.best_fitness,
                "uniformity": result.uniformity,
                "iterations": result.iterations,
                "execution_time": result.execution_time
            }
            self.db_manager.write_optimization_result(task_id, result_record)

            logger.info(f"Optimization task {task_id} completed successfully")
            logger.info(f"Best uniformity: {result.uniformity:.4f}, Avg illuminance: {result.avg_illuminance:.2f}")

        except Exception as e:
            logger.error(f"Optimization task {task_id} failed: {e}", exc_info=True)
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

    def compare_solutions(
        self,
        original_windows: Optional[List[Dict]] = None,
        optimized_windows: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        try:
            building = BuildingGeometry()
            calculator = LightingCalculator(
                building=building,
                latitude=settings.latitude,
                longitude=settings.longitude,
                grid_resolution=10
            )

            eval_times = [
                datetime(datetime.now().year, 1, 15, 10),
                datetime(datetime.now().year, 1, 15, 12),
                datetime(datetime.now().year, 1, 15, 14),
            ]

            if original_windows:
                calculator.update_windows(original_windows)

            original_metrics = self._evaluate_windows(calculator, eval_times)

            if optimized_windows:
                calculator.update_windows(optimized_windows)

            optimized_metrics = self._evaluate_windows(calculator, eval_times)

            improvement = {
                "uniformity_improvement": (
                    (optimized_metrics["avg_uniformity"] - original_metrics["avg_uniformity"]) /
                    max(0.001, original_metrics["avg_uniformity"]) * 100
                ),
                "illuminance_improvement": (
                    (optimized_metrics["avg_illuminance"] - original_metrics["avg_illuminance"]) /
                    max(0.001, original_metrics["avg_illuminance"]) * 100
                )
            }

            return {
                "status": "success",
                "original": original_metrics,
                "optimized": optimized_metrics,
                "improvement": improvement
            }

        except Exception as e:
            logger.error(f"Error comparing solutions: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def _evaluate_windows(
        self,
        calculator: LightingCalculator,
        eval_times: List[datetime]
    ) -> Dict[str, Any]:
        uniformities = []
        avg_illuminances = []
        max_illuminances = []
        min_illuminances = []

        for dt in eval_times:
            result = calculator.calculate_illuminance(dt)
            uniformities.append(result.uniformity)
            avg_illuminances.append(result.avg_illuminance)
            max_illuminances.append(result.max_illuminance)
            min_illuminances.append(result.min_illuminance)

        return {
            "avg_uniformity": float(np.mean(uniformities)),
            "avg_illuminance": float(np.mean(avg_illuminances)),
            "max_illuminance": float(np.mean(max_illuminances)),
            "min_illuminance": float(np.mean(min_illuminances))
        }


def get_optimization_service() -> OptimizationService:
    return OptimizationService()
