#!/usr/bin/env python3
"""
era_comparator 模块 — 古代明堂与现代建筑采光标准跨时代对比
独立封装标准对比逻辑，统一数据格式
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from shared.config import load_json_config

logger = logging.getLogger(__name__)

REFERENCE_ILLUMINANCE = 10000.0


@dataclass
class SimulatedMetrics:
    daylight_factor_min: float
    daylight_factor_avg: float
    illuminance_min: float
    illuminance_avg: float
    uniformity_min: float
    dgp_max: float = 0.35
    da300: float = 0.0
    udi_100_3000: float = 0.0

    @classmethod
    def from_raw(cls, avg_illuminance: float, min_illuminance: float,
                 uniformity: float) -> "SimulatedMetrics":
        df_min = (min_illuminance / REFERENCE_ILLUMINANCE) * 100
        df_avg = (avg_illuminance / REFERENCE_ILLUMINANCE) * 100
        da300 = min(100.0, avg_illuminance / 5.0) if avg_illuminance > 0 else 0.0
        udi = min(100.0, (1 - abs(avg_illuminance - 1500) / 3000) * 100) if avg_illuminance > 0 else 0.0
        return cls(
            daylight_factor_min=round(df_min, 2),
            daylight_factor_avg=round(df_avg, 2),
            illuminance_min=round(min_illuminance, 1),
            illuminance_avg=round(avg_illuminance, 1),
            uniformity_min=round(uniformity, 3),
            da300=round(da300, 1),
            udi_100_3000=round(udi, 1)
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "daylight_factor_min": self.daylight_factor_min,
            "daylight_factor_avg": self.daylight_factor_avg,
            "illuminance_min": self.illuminance_min,
            "illuminance_avg": self.illuminance_avg,
            "uniformity_min": self.uniformity_min,
            "dgp_max": self.dgp_max,
            "da300": self.da300,
            "udi_100_3000": self.udi_100_3000,
        }


@dataclass
class CategoryCompliance:
    category_key: str
    category_label: str
    standard_value: float
    simulated_value: float
    unit: str
    compliance_ratio: float
    passed: bool
    score: float
    weight: float


@dataclass
class StandardComparisonResult:
    standard_key: str
    standard_name: str
    short_code: str
    region: str
    year: int
    category: str
    overall_score: float
    pass_count: int
    total_count: int
    simulated: SimulatedMetrics
    compliance: List[CategoryCompliance] = field(default_factory=list)

    def to_dict(self, dynasty_key: str = "", dynasty_name: str = "") -> Dict[str, Any]:
        compliance_dict = {}
        for c in self.compliance:
            compliance_dict[c.category_key] = {
                "standard_value": c.standard_value,
                "simulated_value": c.simulated_value,
                "unit": c.unit,
                "compliance_ratio": round(c.compliance_ratio, 3),
                "pass": c.passed,
            }
        return {
            "standard_key": self.standard_key,
            "standard_name": self.standard_name,
            "short_code": self.short_code,
            "country": self.region,
            "year": self.year,
            "category": self.category,
            "dynasty": dynasty_key,
            "dynasty_name": dynasty_name,
            "simulated_metrics": self.simulated.to_dict(),
            "standards_compliance": compliance_dict,
            "overall_score": round(self.overall_score, 3),
            "pass_count": self.pass_count,
            "total_count": self.total_count,
        }


class EraComparator:
    """跨时代采光标准对比分析器"""

    def __init__(self):
        self._standards_config = None
        self._dynasty_config = None

    @property
    def standards_config(self) -> Dict[str, Any]:
        if self._standards_config is None:
            self._standards_config = load_json_config("standards_params.json")
        return self._standards_config

    @property
    def dynasty_config(self) -> Dict[str, Any]:
        if self._dynasty_config is None:
            self._dynasty_config = load_json_config("dynasty_params.json")
        return self._dynasty_config

    def list_standards(self) -> List[Dict[str, Any]]:
        """列出所有可用的采光标准（现代+古代）"""
        cfg = self.standards_config
        all_standards = []

        for std in cfg.get("modern_standards", []):
            all_standards.append({
                "key": std["key"],
                "short_code": std.get("short_code", std["key"]),
                "name": std["full_name"],
                "region": std["region"],
                "year": std["year"],
                "category": std.get("category", "modern"),
            })

        for std in cfg.get("ancient_benchmarks", []):
            all_standards.append({
                "key": std["key"],
                "short_code": std.get("short_code", std["key"]),
                "name": std["full_name"],
                "region": std["region"],
                "year": std["year"],
                "category": std.get("category", "historical"),
            })

        return all_standards

    def _get_standards_db(self) -> List[Dict[str, Any]]:
        cfg = self.standards_config
        modern = cfg.get("modern_standards", [])
        ancient = cfg.get("ancient_benchmarks", [])
        return list(modern) + list(ancient)

    def compare(self, dynasty_key: str, avg_illuminance: float,
                min_illuminance: float, uniformity: float) -> List[Dict[str, Any]]:
        """
        对比明堂实测值与所有采光标准
        :return: 各标准对比结果
        """
        simulated = SimulatedMetrics.from_raw(avg_illuminance, min_illuminance, uniformity)
        standards = self._get_standards_db()
        categories = self.standards_config.get("comparison_categories", [])

        dynasty_data = self.dynasty_config.get("dynasties", {}).get(dynasty_key, {})
        d_name = dynasty_data.get("name", dynasty_key)

        results = []
        for std in standards:
            std_metrics = std.get("metrics", {})
            compliance_list = []
            total_score = 0.0
            total_weight = 0.0
            pass_count = 0

            for cat in categories:
                cat_key = cat["key"]
                cat_label = cat["label"]
                cat_weight = cat["weight"]
                cat_unit = cat.get("unit", "")

                std_value = std_metrics.get(cat_key, {}).get("value", 0.0) \
                    if isinstance(std_metrics.get(cat_key), dict) else std_metrics.get(cat_key, 0.0)

                sim_value = getattr(simulated, cat_key, 0.0)

                if std_value > 0:
                    ratio = min(sim_value / std_value, 1.5) if std_value != 0 else 1.5
                    score = min(1.0, ratio)
                    passed = sim_value >= std_value
                else:
                    ratio = 1.0
                    score = 1.0
                    passed = True

                if passed:
                    pass_count += 1

                compliance_list.append(CategoryCompliance(
                    category_key=cat_key,
                    category_label=cat_label,
                    standard_value=std_value,
                    simulated_value=round(sim_value, 2),
                    unit=cat_unit,
                    compliance_ratio=round(ratio, 3),
                    passed=passed,
                    score=round(score, 3),
                    weight=cat_weight,
                ))
                total_score += score * cat_weight
                total_weight += cat_weight

            overall = total_score / total_weight if total_weight > 0 else 0.0

            result_obj = StandardComparisonResult(
                standard_key=std["key"],
                standard_name=std["full_name"],
                short_code=std.get("short_code", std["key"]),
                region=std["region"],
                year=std["year"],
                category=std.get("category", "modern"),
                overall_score=overall,
                pass_count=pass_count,
                total_count=len(categories),
                simulated=simulated,
                compliance=compliance_list,
            )
            results.append(result_obj.to_dict(dynasty_key, d_name))

        return results

    def get_compliance_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成合规性总览统计"""
        if not results:
            return {}
        modern = [r for r in results if r.get("category") != "historical"]
        ancient = [r for r in results if r.get("category") == "historical"]

        avg_modern_score = sum(r["overall_score"] for r in modern) / len(modern) if modern else 0
        avg_ancient_score = sum(r["overall_score"] for r in ancient) / len(ancient) if ancient else 0
        best = max(results, key=lambda r: r["overall_score"]) if results else None

        return {
            "modern_standards_count": len(modern),
            "ancient_benchmarks_count": len(ancient),
            "avg_modern_score": round(avg_modern_score, 3),
            "avg_ancient_score": round(avg_ancient_score, 3),
            "best_standard": best["standard_key"] if best else None,
            "best_score": round(best["overall_score"], 3) if best else 0,
        }


_era_comparator_instance: Optional[EraComparator] = None


def get_era_comparator() -> EraComparator:
    global _era_comparator_instance
    if _era_comparator_instance is None:
        _era_comparator_instance = EraComparator()
    return _era_comparator_instance
