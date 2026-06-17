#!/usr/bin/env python3
"""
FeatureService — 4个新增功能的统一门面服务
重构后：核心计算逻辑分别委托给独立模块
- design_comparator: 朝代对比
- era_comparator: 跨时代标准对比
- tree_shadow_simulator: 树木影响
- vr_mingtang: 虚拟参观
可选：通过 ray_tracer_worker 进程池执行CPU密集计算
"""
import logging
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

from shared.database import get_db_manager, InfluxDBManager
from shared.redis_client import get_redis_client, RedisClient
from shared.schemas import (
    DynastyComparisonParams, DynastySimulationResult,
    TreeImpactParams, TreeImpactResult,
    VirtualTourParams, VirtualTourResult,
    TaskStatus, RedisChannels
)
from ..features import (
    get_design_comparator,
    get_era_comparator,
    get_tree_shadow_simulator,
    get_vr_mingtang_tour,
)

logger = logging.getLogger(__name__)

USE_WORKER_PROCESS = False


class FeatureService:
    def __init__(self, use_worker: bool = USE_WORKER_PROCESS):
        self._init_core(use_worker)

    def _init_core(self, use_worker: bool = USE_WORKER_PROCESS):
        """惰性初始化核心组件，兼容__new__跳过__init__的场景"""
        if not hasattr(self, 'tasks') or self.tasks is None:
            self.tasks: Dict[str, Dict[str, Any]] = {}
        if not hasattr(self, 'use_worker'):
            self.use_worker = use_worker
        if not hasattr(self, 'db_manager'):
            try:
                self.db_manager: InfluxDBManager = get_db_manager()
            except Exception:
                self.db_manager = None
        if not hasattr(self, 'redis_client'):
            try:
                self.redis_client: RedisClient = get_redis_client()
            except Exception:
                self.redis_client = None
        if not hasattr(self, '_design_cmp') or self._design_cmp is None:
            self._design_cmp = get_design_comparator()
        if not hasattr(self, '_era_cmp') or self._era_cmp is None:
            self._era_cmp = get_era_comparator()
        if not hasattr(self, '_tree_sim') or self._tree_sim is None:
            self._tree_sim = get_tree_shadow_simulator()
        if not hasattr(self, '_vr_tour') or self._vr_tour is None:
            self._vr_tour = get_vr_mingtang_tour()
        if not hasattr(self, '_worker_mgr'):
            self._worker_mgr = None
            if self.use_worker:
                try:
                    from ..workers import get_ray_tracer_worker_manager
                    self._worker_mgr = get_ray_tracer_worker_manager(num_workers=1)
                    self._worker_mgr.start()
                    logger.info("FeatureService 已启用光线追踪Worker进程")
                except Exception as e:
                    logger.warning(f"Worker进程启动失败，回退到同步计算: {e}")
                    self.use_worker = False

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

    # ==================== Feature 1: 朝代对比 ====================

    def compare_dynasties(self, params: DynastyComparisonParams) -> Dict[str, Any]:
        self._init_core()
        task_id = self._create_task("dynasty_cmp")
        asyncio.create_task(self._run_dynasty_comparison(task_id, params))
        return {"task_id": task_id, "status": TaskStatus.RUNNING.value}

    async def _run_dynasty_comparison(self, task_id: str, params: DynastyComparisonParams):
        try:
            self.tasks[task_id]["status"] = TaskStatus.RUNNING.value
            total = len(params.dynasties)

            def _progress(curr, tot):
                self.tasks[task_id]["progress"] = curr / tot

            if self.use_worker and self._worker_mgr is not None:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self._design_cmp.compare_illuminance(params, progress_callback=_progress)
                )
            else:
                result = self._design_cmp.compare_illuminance(params, progress_callback=_progress)
                for i in range(total):
                    self.tasks[task_id]["progress"] = (i + 1) / total
                    await asyncio.sleep(0.05)

            self.tasks[task_id]["status"] = TaskStatus.COMPLETED.value
            self.tasks[task_id]["progress"] = 1.0
            self.tasks[task_id]["result"] = [r.model_dump() for r in result]

        except Exception as e:
            logger.error(f"朝代对比任务失败 {task_id}: {e}")
            self.tasks[task_id]["status"] = TaskStatus.FAILED.value
            self.tasks[task_id]["error"] = str(e)

    # ==================== Feature 2: 跨时代标准对比 ====================

    def compare_standards(self, dynasty_key: str, avg_illuminance: float,
                          min_illuminance: float, uniformity: float) -> List[Dict[str, Any]]:
        self._init_core()
        return self._era_cmp.compare(dynasty_key, avg_illuminance, min_illuminance, uniformity)

    # ==================== Feature 3: 树木影响 ====================

    def simulate_tree_impact(self, params: TreeImpactParams) -> Dict[str, Any]:
        self._init_core()
        task_id = self._create_task("tree_impact")
        asyncio.create_task(self._run_tree_impact(task_id, params))
        return {"task_id": task_id, "status": TaskStatus.RUNNING.value}

    async def _run_tree_impact(self, task_id: str, params: TreeImpactParams):
        try:
            self.tasks[task_id]["status"] = TaskStatus.RUNNING.value

            def _progress(p):
                self.tasks[task_id]["progress"] = p

            if self.use_worker and self._worker_mgr is not None:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self._tree_sim.simulate(params, progress_callback=_progress)
                )
            else:
                self.tasks[task_id]["progress"] = 0.5
                await asyncio.sleep(0.05)
                result = self._tree_sim.simulate(params, progress_callback=_progress)
                await asyncio.sleep(0.05)

            self.tasks[task_id]["status"] = TaskStatus.COMPLETED.value
            self.tasks[task_id]["progress"] = 1.0
            self.tasks[task_id]["result"] = result.model_dump()

        except Exception as e:
            logger.error(f"树木影响仿真失败 {task_id}: {e}")
            self.tasks[task_id]["status"] = TaskStatus.FAILED.value
            self.tasks[task_id]["error"] = str(e)

    # ==================== Feature 4: 虚拟参观 ====================

    def virtual_tour(self, params: VirtualTourParams) -> Dict[str, Any]:
        self._init_core()
        task_id = self._create_task("vtour")
        asyncio.create_task(self._run_virtual_tour(task_id, params))
        return {"task_id": task_id, "status": TaskStatus.RUNNING.value}

    async def _run_virtual_tour(self, task_id: str, params: VirtualTourParams):
        try:
            self.tasks[task_id]["status"] = TaskStatus.RUNNING.value

            def _progress(p):
                self.tasks[task_id]["progress"] = p

            if self.use_worker and self._worker_mgr is not None:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self._vr_tour.run_tour(params, progress_callback=_progress)
                )
            else:
                result = self._vr_tour.run_tour(params, progress_callback=_progress)
                total_minutes = max(1, (params.end_hour - params.start_hour) * 60)
                elapsed = 0
                while elapsed < total_minutes:
                    elapsed += params.time_step
                    self.tasks[task_id]["progress"] = min(elapsed / total_minutes, 1.0)
                    await asyncio.sleep(0.05)

            self.tasks[task_id]["status"] = TaskStatus.COMPLETED.value
            self.tasks[task_id]["progress"] = 1.0
            self.tasks[task_id]["result"] = result.model_dump()

        except Exception as e:
            logger.error(f"虚拟参观仿真失败 {task_id}: {e}")
            self.tasks[task_id]["status"] = TaskStatus.FAILED.value
            self.tasks[task_id]["error"] = str(e)

    # ==================== 通用 ====================

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        self._init_core()
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

    def shutdown(self):
        """关闭Worker进程等资源"""
        if self._worker_mgr:
            self._worker_mgr.stop()
            self._worker_mgr = None


_service_instance: Optional[FeatureService] = None


def get_feature_service() -> FeatureService:
    global _service_instance
    if _service_instance is None:
        _service_instance = FeatureService()
    return _service_instance
