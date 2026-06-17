#!/usr/bin/env python3
"""
tree_shadow_simulator 模块 — 庭院树木对明堂采光的影响仿真
独立封装树木几何构建、季节因子、阴影计算逻辑
"""
import logging
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from shared.config import load_json_config
from daylight_simulator.simulation.lighting_calc import LightingCalculator
from shared.schemas import TreeImpactParams, TreeImpactResult

logger = logging.getLogger(__name__)


@dataclass
class TreeSpecies:
    key: str
    name: str
    trunk_radius: float
    trunk_height: float
    canopy_radius: float
    canopy_height: float
    canopy_transmittance: float
    albedo: List[float]
    leaf_density: float


@dataclass
class TreeInstance:
    species_key: str
    position: List[float]
    scale: float = 1.0
    season: str = "summer"
    species: Optional[TreeSpecies] = None

    def effective_transmittance(self, seasonal_factor: float) -> float:
        if self.species is None:
            return 0.35
        base_t = self.species.canopy_transmittance
        leaf_factor = seasonal_factor * self.species.leaf_density
        return max(0.05, min(0.95, base_t * (1.0 - 0.7 * leaf_factor)))

    def to_config_dict(self) -> Dict[str, Any]:
        return {
            "species": self.species_key,
            "position": list(self.position),
            "scale": self.scale,
        }


@dataclass
class SeasonalFactor:
    season: str
    leaf_factor: float
    description: str


@dataclass
class IlluminanceSnapshot:
    avg_illuminance: float
    min_illuminance: float
    max_illuminance: float
    uniformity: float
    illuminance_matrix: np.ndarray

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_illuminance": float(self.avg_illuminance),
            "min_illuminance": float(self.min_illuminance),
            "max_illuminance": float(self.max_illuminance),
            "uniformity": float(self.uniformity),
            "illuminance_matrix": self.illuminance_matrix.tolist()
        }


class TreeShadowSimulator:
    """庭院树木阴影仿真器"""

    SEASON_KEYS = ["spring", "summer", "autumn", "winter"]

    def __init__(self):
        self._tree_config = None

    @property
    def tree_config(self) -> Dict[str, Any]:
        if self._tree_config is None:
            self._tree_config = load_json_config("tree_params.json")
        return self._tree_config

    def list_species(self) -> List[Dict[str, Any]]:
        """列出所有可用树种"""
        species_db = self.tree_config.get("tree_species", {})
        result = []
        for key, sp in species_db.items():
            result.append({
                "key": key,
                "name": sp.get("name", key),
                "trunk_radius": sp.get("trunk_radius", 0.3),
                "trunk_height": sp.get("trunk_height", 5.0),
                "canopy_radius": sp.get("canopy_radius", 3.5),
                "canopy_height": sp.get("canopy_height", 4.0),
                "canopy_transmittance": sp.get("canopy_transmittance", 0.35),
                "leaf_density": sp.get("leaf_density", 0.6),
                "albedo": sp.get("albedo", [0.2, 0.4, 0.1]),
            })
        return result

    def get_species(self, key: str) -> TreeSpecies:
        """获取单个树种定义"""
        species_db = self.tree_config.get("tree_species", {})
        sp = species_db.get(key, species_db.get("pine", {}))
        return TreeSpecies(
            key=key,
            name=sp.get("name", key),
            trunk_radius=sp.get("trunk_radius", 0.3),
            trunk_height=sp.get("trunk_height", 5.0),
            canopy_radius=sp.get("canopy_radius", 3.5),
            canopy_height=sp.get("canopy_height", 4.0),
            canopy_transmittance=sp.get("canopy_transmittance", 0.35),
            albedo=sp.get("albedo", [0.2, 0.4, 0.1]),
            leaf_density=sp.get("leaf_density", 0.6),
        )

    def get_season_factor(self, season: str) -> SeasonalFactor:
        """获取季节因子"""
        seasons = self.tree_config.get("seasonal_factors", {})
        season = season if season in seasons else "summer"
        sf = seasons.get(season, {"leaf_factor": 1.0, "description": ""})
        return SeasonalFactor(
            season=season,
            leaf_factor=sf.get("leaf_factor", 1.0),
            description=sf.get("description", "")
        )

    def get_default_layout(self) -> List[TreeInstance]:
        """获取默认庭院树木布局"""
        layout = self.tree_config.get("default_layout", {}).get("trees", [])
        instances = []
        for t_cfg in layout:
            sp_key = t_cfg.get("species", "pine")
            instances.append(TreeInstance(
                species_key=sp_key,
                position=list(t_cfg.get("position", [0, 0, 0])),
                scale=t_cfg.get("scale", 1.0),
                species=self.get_species(sp_key)
            ))
        return instances

    def _build_tree_list(self, params: TreeImpactParams) -> List[Dict[str, Any]]:
        """从参数构建树木配置列表"""
        if params.trees and len(params.trees) > 0:
            return [t.model_dump() for t in params.trees]
        layout = self.tree_config.get("default_layout", {}).get("trees", [])
        return list(layout)

    def _collect_tree_details(self, trees_cfg: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """汇总树木详情"""
        species_db = self.tree_config.get("tree_species", {})
        details = []
        for t_cfg in trees_cfg:
            sp_key = t_cfg.get("species", "pine")
            sp = species_db.get(sp_key, species_db.get("pine", {}))
            scale = t_cfg.get("scale", 1.0)
            details.append({
                "species": sp_key,
                "species_name": sp.get("name", sp_key),
                "position": list(t_cfg.get("position", [0, 0, 0])),
                "scale": scale,
                "canopy_radius": sp.get("canopy_radius", 3.5) * scale,
                "canopy_height": sp.get("canopy_height", 4.0) * scale,
                "trunk_height": sp.get("trunk_height", 5.0) * scale,
                "canopy_transmittance": sp.get("canopy_transmittance", 0.35),
                "leaf_density": sp.get("leaf_density", 0.6),
            })
        return details

    def simulate(self, params: TreeImpactParams,
                 progress_callback=None) -> TreeImpactResult:
        """
        执行树木影响仿真
        :param params: 仿真参数（朝代、树木、季节、日期、时刻等）
        :param progress_callback: 进度回调 callback(0.0~1.0)
        :return: 树木影响结果（有/无树对比 + 统计指标）
        """
        dynasty_key = params.dynasty.value

        calculator = LightingCalculator.from_dynasty(dynasty_key, params.grid_resolution)
        dt = datetime.strptime(params.date, "%Y-%m-%d").replace(hour=params.hour)

        result_without = calculator.calculate_illuminance(
            dt, sky_model_type=params.sky_model.value, turbidity=params.turbidity
        )
        without = IlluminanceSnapshot(
            avg_illuminance=float(result_without.avg_illuminance),
            min_illuminance=float(result_without.min_illuminance),
            max_illuminance=float(result_without.max_illuminance),
            uniformity=float(result_without.uniformity),
            illuminance_matrix=result_without.illuminance_matrix
        )

        if progress_callback:
            progress_callback(0.5)

        trees_cfg = self._build_tree_list(params)
        calculator.add_trees(trees_cfg, params.season)

        result_with = calculator.calculate_illuminance(
            dt, sky_model_type=params.sky_model.value, turbidity=params.turbidity
        )
        with_trees = IlluminanceSnapshot(
            avg_illuminance=float(result_with.avg_illuminance),
            min_illuminance=float(result_with.min_illuminance),
            max_illuminance=float(result_with.max_illuminance),
            uniformity=float(result_with.uniformity),
            illuminance_matrix=result_with.illuminance_matrix
        )

        reduction = 0.0
        if without.avg_illuminance > 0:
            reduction = (1 - with_trees.avg_illuminance / without.avg_illuminance) * 100

        uniformity_change = with_trees.uniformity - without.uniformity

        diff_matrix = without.illuminance_matrix - with_trees.illuminance_matrix
        shaded_pct = float(np.sum(diff_matrix > 10) / diff_matrix.size * 100) if diff_matrix.size > 0 else 0

        tree_details = self._collect_tree_details(trees_cfg)

        if progress_callback:
            progress_callback(1.0)

        return TreeImpactResult(
            without_trees=without.to_dict(),
            with_trees=with_trees.to_dict(),
            illuminance_reduction_pct=round(reduction, 2),
            uniformity_change=round(uniformity_change, 4),
            shaded_area_pct=round(shaded_pct, 1),
            tree_details=tree_details
        )

    def estimate_shadow_radius(self, tree: TreeInstance, solar_altitude_deg: float) -> float:
        """
        估算单棵树在给定太阳高度角下的地面阴影半径（简化解析模型）
        :param tree: 树木实例
        :param solar_altitude_deg: 太阳高度角（度）
        :return: 阴影半径（米）
        """
        if solar_altitude_deg <= 0:
            return 0.0
        if tree.species is None:
            tree.species = self.get_species(tree.species_key)
        total_h = (tree.species.trunk_height + tree.species.canopy_height) * tree.scale
        canopy_r = tree.species.canopy_radius * tree.scale
        tan_alt = np.tan(np.radians(solar_altitude_deg))
        if tan_alt <= 0:
            return 0.0
        shadow_from_top = total_h / tan_alt
        return max(canopy_r, shadow_from_top + canopy_r * 0.5)


_tree_shadow_instance: Optional[TreeShadowSimulator] = None


def get_tree_shadow_simulator() -> TreeShadowSimulator:
    global _tree_shadow_instance
    if _tree_shadow_instance is None:
        _tree_shadow_instance = TreeShadowSimulator()
    return _tree_shadow_instance
