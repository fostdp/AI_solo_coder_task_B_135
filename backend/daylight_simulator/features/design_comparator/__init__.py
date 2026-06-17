#!/usr/bin/env python3
"""
design_comparator 模块 — 不同朝代明堂采光设计对比
独立封装朝代对比逻辑，不依赖 FeatureService
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from shared.config import load_json_config
from daylight_simulator.simulation.lighting_calc import LightingCalculator
from shared.schemas import DynastyComparisonParams, DynastySimulationResult

logger = logging.getLogger(__name__)


@dataclass
class DynastyDesignSummary:
    dynasty: str
    dynasty_name: str
    year: str
    building_specs: Dict[str, Any]
    window_material: str
    window_transmittance: float
    latitude: float
    longitude: float


class DesignComparator:
    """不同朝代明堂采光设计对比分析器"""

    def __init__(self):
        self._dynasty_config = None

    @property
    def dynasty_config(self) -> Dict[str, Any]:
        if self._dynasty_config is None:
            self._dynasty_config = load_json_config("dynasty_params.json")
        return self._dynasty_config

    def list_dynasties(self) -> List[Dict[str, Any]]:
        """列出所有可用朝代的基本信息"""
        dynasties_db = self.dynasty_config.get("dynasties", {})
        result = []
        for key, data in dynasties_db.items():
            building = data.get("building", {})
            materials = data.get("materials", {}).get("window", {})
            result.append({
                "key": key,
                "name": data.get("name", key),
                "year": data.get("year", ""),
                "latitude": data.get("latitude", 0),
                "longitude": data.get("longitude", 0),
                "building_size": {
                    "length": building.get("length", 0),
                    "width": building.get("width", 0),
                    "height": building.get("height", 0),
                },
                "window_transmittance": materials.get("transmittance", 0.5),
                "window_material": materials.get("name", "unknown"),
                "description": data.get("description", "")
            })
        return result

    def get_dynasty_summary(self, dynasty_key: str) -> Optional[DynastyDesignSummary]:
        """获取单个朝代的设计概要"""
        dynasties_db = self.dynasty_config.get("dynasties", {})
        data = dynasties_db.get(dynasty_key, dynasties_db.get("han", None))
        if data is None:
            return None

        building = data.get("building", {})
        materials = data.get("materials", {}).get("window", {})
        return DynastyDesignSummary(
            dynasty=dynasty_key,
            dynasty_name=data.get("name", dynasty_key),
            year=data.get("year", ""),
            building_specs={
                "length": building.get("length", 20),
                "width": building.get("width", 20),
                "height": building.get("height", 12),
                "roof_type": building.get("roof_type", "pyramidal"),
                "windows_count": len(building.get("default_windows", [])),
            },
            window_material=materials.get("name", "unknown"),
            window_transmittance=materials.get("transmittance", 0.5),
            latitude=data.get("latitude", 0),
            longitude=data.get("longitude", 0)
        )

    def compare_illuminance(self, params: DynastyComparisonParams,
                            progress_callback=None) -> List[DynastySimulationResult]:
        """
        执行多朝代照度对比仿真
        :param params: 对比参数（朝代列表、日期、时刻、天空模型等）
        :param progress_callback: 进度回调函数 callback(current_idx, total)
        :return: 各朝代仿真结果列表
        """
        dynasties_db = self.dynasty_config.get("dynasties", {})
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
            windows = building_cfg.get("default_windows", [])
            window_trans = windows[0].get("transmittance", 0.5) if windows else 0.5

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
                    "windows_count": len(windows),
                    "window_transmittance": window_trans
                }
            ))

            if progress_callback:
                progress_callback(i + 1, total)

        return results

    @staticmethod
    def rank_by_avg_illuminance(results: List[DynastySimulationResult]) -> List[Dict[str, Any]]:
        """按平均照度降序排名"""
        ranked = sorted(results, key=lambda r: r.avg_illuminance, reverse=True)
        return [
            {
                "rank": idx + 1,
                "dynasty": r.dynasty,
                "dynasty_name": r.dynasty_name,
                "avg_illuminance": r.avg_illuminance,
                "uniformity": r.uniformity
            }
            for idx, r in enumerate(ranked)
        ]


_design_comparator_instance: Optional[DesignComparator] = None


def get_design_comparator() -> DesignComparator:
    global _design_comparator_instance
    if _design_comparator_instance is None:
        _design_comparator_instance = DesignComparator()
    return _design_comparator_instance
