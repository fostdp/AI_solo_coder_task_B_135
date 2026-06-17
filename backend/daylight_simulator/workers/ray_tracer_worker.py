#!/usr/bin/env python3
"""
ray_tracer_worker 模块 — 独立光线追踪计算进程
使用 multiprocessing 将CPU密集型光线追踪计算从主API进程分离
支持任务队列、进度回调、结果缓存
"""
import logging
import multiprocessing as mp
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from enum import Enum

logger = logging.getLogger(__name__)


class WorkerTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkerTask:
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    status: WorkerTaskStatus = WorkerTaskStatus.PENDING
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


def _worker_process_entry(task_queue: mp.Queue, result_queue: mp.Queue,
                          log_level: int = logging.INFO):
    """
    Worker子进程入口函数
    在独立进程中执行光线追踪计算，避免阻塞主API进程
    """
    logging.basicConfig(level=log_level,
                        format='[Worker %(process)d] %(asctime)s [%(levelname)s] %(message)s')
    logger.info("光线追踪Worker进程启动")

    import sys
    import os
    worker_dir = os.path.dirname(os.path.abspath(__file__))
    backend_root = os.path.abspath(os.path.join(worker_dir, '..', '..'))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    sim_dir = os.path.abspath(os.path.join(worker_dir, '..'))
    if sim_dir not in sys.path:
        sys.path.insert(0, sim_dir)

    try:
        while True:
            try:
                task = task_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if task is None or task.get("__shutdown__"):
                logger.info("Worker进程收到关闭信号，退出")
                break

            task_id = task.get("task_id")
            task_type = task.get("task_type")
            payload = task.get("payload", {})

            try:
                result_queue.put({
                    "task_id": task_id,
                    "type": "status",
                    "status": WorkerTaskStatus.RUNNING.value,
                    "progress": 0.0
                })
                result_data = _execute_task(task_type, payload, task_id, result_queue)
                result_queue.put({
                    "task_id": task_id,
                    "type": "result",
                    "status": WorkerTaskStatus.COMPLETED.value,
                    "progress": 1.0,
                    "result": result_data,
                    "completed_at": time.time()
                })
            except Exception as e:
                logger.error(f"Worker任务 {task_id} 失败: {e}")
                result_queue.put({
                    "task_id": task_id,
                    "type": "result",
                    "status": WorkerTaskStatus.FAILED.value,
                    "progress": 0.0,
                    "error": str(e)
                })
    except Exception as e:
        logger.error(f"Worker进程异常: {e}")
    finally:
        logger.info("光线追踪Worker进程退出")


def _execute_task(task_type: str, payload: Dict[str, Any],
                  task_id: str, result_queue: mp.Queue) -> Dict[str, Any]:
    """根据任务类型分派到具体模块执行"""
    from datetime import datetime

    if task_type == "illuminance_single":
        return _exec_illuminance_single(payload)

    elif task_type == "dynasty_comparison":
        return _exec_dynasty_comparison(payload, result_queue, task_id)

    elif task_type == "tree_impact":
        return _exec_tree_impact(payload, result_queue, task_id)

    elif task_type == "virtual_tour":
        return _exec_virtual_tour(payload, result_queue, task_id)

    else:
        raise ValueError(f"未知任务类型: {task_type}")


def _exec_illuminance_single(payload: Dict[str, Any]) -> Dict[str, Any]:
    """单次照度计算（最小粒度）"""
    from daylight_simulator.simulation.lighting_calc import LightingCalculator

    dynasty = payload.get("dynasty", "han")
    grid_res = payload.get("grid_resolution", 8)
    date_str = payload.get("date", "2024-06-21")
    hour = payload.get("hour", 12)
    sky_model = payload.get("sky_model", "perez")
    turbidity = payload.get("turbidity", 2.5)
    trees = payload.get("trees", [])
    season = payload.get("season", "summer")

    calc = LightingCalculator.from_dynasty(dynasty, grid_res)
    if trees:
        calc.add_trees(trees, season)
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=hour)
    result = calc.calculate_illuminance(dt, sky_model_type=sky_model, turbidity=turbidity)

    return {
        "avg_illuminance": float(result.avg_illuminance),
        "min_illuminance": float(result.min_illuminance),
        "max_illuminance": float(result.max_illuminance),
        "uniformity": float(result.uniformity),
        "illuminance_matrix": result.illuminance_matrix.tolist(),
        "solar_altitude": float(result.solar_altitude),
        "solar_azimuth": float(result.solar_azimuth),
        "grid_size": list(result.grid_size),
    }


def _exec_dynasty_comparison(payload: Dict[str, Any],
                              result_queue: mp.Queue, task_id: str) -> Dict[str, Any]:
    """朝代对比计算"""
    from daylight_simulator.features import get_design_comparator
    from shared.schemas import DynastyComparisonParams, SkyModel, DynastyKey

    dynasties = [DynastyKey(d) for d in payload.get("dynasties", ["han", "tang", "ming"])]
    params = DynastyComparisonParams(
        dynasties=dynasties,
        date=payload.get("date", "2024-06-21"),
        hour=payload.get("hour", 12),
        grid_resolution=payload.get("grid_resolution", 8),
        sky_model=SkyModel(payload.get("sky_model", "perez")),
        turbidity=payload.get("turbidity", 2.5),
    )
    dc = get_design_comparator()

    def _progress(curr, total):
        result_queue.put({
            "task_id": task_id,
            "type": "status",
            "status": "running",
            "progress": curr / total
        })

    results = dc.compare_illuminance(params, progress_callback=_progress)
    return {"results": [r.model_dump() for r in results]}


def _exec_tree_impact(payload: Dict[str, Any],
                      result_queue: mp.Queue, task_id: str) -> Dict[str, Any]:
    """树木影响计算"""
    from daylight_simulator.features import get_tree_shadow_simulator
    from shared.schemas import TreeImpactParams, SkyModel, DynastyKey, TreeConfig

    dynasty = DynastyKey(payload.get("dynasty", "han"))
    season = payload.get("season", "summer")
    trees_cfg = payload.get("trees", [])
    trees = [TreeConfig(**t) for t in trees_cfg] if trees_cfg else None

    params = TreeImpactParams(
        dynasty=dynasty,
        season=season,
        trees=trees,
        date=payload.get("date", "2024-06-21"),
        hour=payload.get("hour", 12),
        grid_resolution=payload.get("grid_resolution", 8),
        sky_model=SkyModel(payload.get("sky_model", "perez")),
        turbidity=payload.get("turbidity", 2.5),
    )
    ts = get_tree_shadow_simulator()

    def _progress(p):
        result_queue.put({
            "task_id": task_id,
            "type": "status",
            "status": "running",
            "progress": p
        })

    result = ts.simulate(params, progress_callback=_progress)
    return result.model_dump()


def _exec_virtual_tour(payload: Dict[str, Any],
                        result_queue: mp.Queue, task_id: str) -> Dict[str, Any]:
    """虚拟参观时序计算"""
    from daylight_simulator.features import get_vr_mingtang_tour
    from shared.schemas import VirtualTourParams, SkyModel, DynastyKey

    params = VirtualTourParams(
        dynasty=DynastyKey(payload.get("dynasty", "han")),
        date=payload.get("date", "2024-06-21"),
        start_hour=payload.get("start_hour", 6),
        end_hour=payload.get("end_hour", 18),
        time_step=payload.get("time_step", 30),
        grid_resolution=payload.get("grid_resolution", 6),
        sky_model=SkyModel(payload.get("sky_model", "perez")),
        turbidity=payload.get("turbidity", 2.5),
    )
    vr = get_vr_mingtang_tour()

    def _progress(p):
        result_queue.put({
            "task_id": task_id,
            "type": "status",
            "status": "running",
            "progress": p
        })

    result = vr.run_tour(params, progress_callback=_progress)
    return result.model_dump()


class RayTracerWorkerManager:
    """
    光线追踪Worker管理器（主进程侧）
    - 管理Worker子进程生命周期
    - 提交任务、查询状态、获取结果
    - 通过多进程队列与子进程通信
    """

    def __init__(self, num_workers: int = 1):
        self.num_workers = max(1, min(num_workers, mp.cpu_count()))
        self._task_queue: Optional[mp.Queue] = None
        self._result_queue: Optional[mp.Queue] = None
        self._processes: List[mp.Process] = []
        self._tasks: Dict[str, WorkerTask] = {}
        self._result_listeners: Dict[str, Callable] = {}
        self._dispatcher_thread: Optional[threading.Thread] = None
        self._shutdown = False
        self._lock = threading.Lock()

    def start(self):
        """启动Worker池和结果分发线程"""
        if self._processes:
            return

        ctx = mp.get_context("spawn")
        self._task_queue = ctx.Queue()
        self._result_queue = ctx.Queue()

        for i in range(self.num_workers):
            p = ctx.Process(
                target=_worker_process_entry,
                args=(self._task_queue, self._result_queue, logging.getLogger().level),
                name=f"RayTracerWorker-{i}",
                daemon=True,
            )
            p.start()
            self._processes.append(p)
            logger.info(f"已启动 Worker 进程 {i} (PID={p.pid})")

        self._dispatcher_thread = threading.Thread(
            target=self._dispatch_results_loop,
            name="RayTracerResultDispatcher",
            daemon=True,
        )
        self._dispatcher_thread.start()

    def stop(self):
        """优雅关闭所有Worker"""
        self._shutdown = True
        for _ in self._processes:
            try:
                self._task_queue.put({"__shutdown__": True})
            except Exception:
                pass

        for p in self._processes:
            p.join(timeout=5.0)
            if p.is_alive():
                p.terminate()

        self._processes.clear()
        logger.info("所有光线追踪Worker已停止")

    def submit_task(self, task_type: str, payload: Dict[str, Any],
                    on_progress: Optional[Callable[[float], None]] = None,
                    on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
                    on_error: Optional[Callable[[str], None]] = None) -> str:
        """
        提交计算任务到Worker进程
        :return: task_id
        """
        if not self._processes:
            self.start()

        task_id = f"rt_{task_type}_{uuid.uuid4().hex[:12]}"
        task = WorkerTask(task_id=task_id, task_type=task_type, payload=payload)

        with self._lock:
            self._tasks[task_id] = task
            self._result_listeners[task_id] = {
                "on_progress": on_progress,
                "on_complete": on_complete,
                "on_error": on_error,
            }

        self._task_queue.put({
            "task_id": task_id,
            "task_type": task_type,
            "payload": payload,
        })
        logger.debug(f"任务已提交: {task_id} ({task_type})")
        return task_id

    def get_task(self, task_id: str) -> Optional[WorkerTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        task = self.get_task(task_id)
        if task is None:
            return {"task_id": task_id, "status": "not_found"}
        return {
            "task_id": task.task_id,
            "status": task.status.value if isinstance(task.status, WorkerTaskStatus) else task.status,
            "progress": task.progress,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
        }

    def _dispatch_results_loop(self):
        """结果分发线程：从结果队列读取并更新任务状态"""
        while not self._shutdown:
            try:
                msg = self._result_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"结果队列读取异常: {e}")
                break

            task_id = msg.get("task_id")
            if not task_id:
                continue

            with self._lock:
                task = self._tasks.get(task_id)
                listeners = self._result_listeners.get(task_id, {})

            if task is None:
                continue

            msg_type = msg.get("type")
            if msg_type == "status":
                task.progress = msg.get("progress", 0.0)
                task.status = WorkerTaskStatus(msg.get("status", "running"))
                if task.started_at is None:
                    task.started_at = time.time()
                cb = listeners.get("on_progress")
                if cb:
                    try:
                        cb(task.progress)
                    except Exception as e:
                        logger.error(f"进度回调异常: {e}")

            elif msg_type == "result":
                task.status = WorkerTaskStatus(msg.get("status", "completed"))
                task.progress = msg.get("progress", 1.0)
                task.completed_at = msg.get("completed_at", time.time())
                if task.status == WorkerTaskStatus.COMPLETED:
                    task.result = msg.get("result")
                    cb = listeners.get("on_complete")
                    if cb:
                        try:
                            cb(task.result)
                        except Exception as e:
                            logger.error(f"完成回调异常: {e}")
                else:
                    task.error = msg.get("error", "Unknown error")
                    cb = listeners.get("on_error")
                    if cb:
                        try:
                            cb(task.error)
                        except Exception as e:
                            logger.error(f"错误回调异常: {e}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


_worker_manager_instance: Optional[RayTracerWorkerManager] = None


def get_ray_tracer_worker_manager(num_workers: int = 1) -> RayTracerWorkerManager:
    global _worker_manager_instance
    if _worker_manager_instance is None:
        _worker_manager_instance = RayTracerWorkerManager(num_workers=num_workers)
    return _worker_manager_instance
