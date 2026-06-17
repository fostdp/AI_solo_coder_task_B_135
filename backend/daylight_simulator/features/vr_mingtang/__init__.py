#!/usr/bin/env python3
"""
vr_mingtang 模块 — 公众虚拟参观明堂体验
独立封装时间序列仿真、太阳轨迹、逐时光照数据
支持时间滑块、自动播放、太阳位置实时更新
"""
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from shared.config import load_json_config
from daylight_simulator.simulation.lighting_calc import LightingCalculator
from shared.schemas import (
    VirtualTourParams, VirtualTourResult, VirtualTourHourData
)

logger = logging.getLogger(__name__)


@dataclass
class SunPosition:
    hour: float
    altitude_deg: float
    azimuth_deg: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "hour": self.hour,
            "altitude": self.altitude_deg,
            "azimuth": self.azimuth_deg
        }


@dataclass
class TourSnapshot:
    hour: float
    sun: SunPosition
    avg_illuminance: float
    min_illuminance: float
    max_illuminance: float
    uniformity: float
    illuminance_matrix: Any


class VRMingtangTour:
    """虚拟参观明堂时序仿真器"""

    MIN_TIME_STEP = 1
    MAX_TIME_STEP = 120

    def __init__(self):
        self._dynasty_config = None

    @property
    def dynasty_config(self) -> Dict[str, Any]:
        if self._dynasty_config is None:
            self._dynasty_config = load_json_config("dynasty_params.json")
        return self._dynasty_config

    def list_dynasties(self) -> List[Dict[str, Any]]:
        """列出可用朝代的虚拟参观基本信息"""
        from daylight_simulator.features.design_comparator import get_design_comparator
        return get_design_comparator().list_dynasties()

    def _build_time_range(self, date_str: str, start_hour: int,
                          end_hour: int, step_minutes: int) -> List[datetime]:
        """构建时间点序列"""
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        step = max(self.MIN_TIME_STEP, min(self.MAX_TIME_STEP, step_minutes))
        times = []
        current = datetime(date_obj.year, date_obj.month, date_obj.day, start_hour)
        end_time = datetime(date_obj.year, date_obj.month, date_obj.day, end_hour)
        while current <= end_time:
            times.append(current)
            current += timedelta(minutes=step)
        return times

    def run_tour(self, params: VirtualTourParams,
                 progress_callback: Optional[Callable[[float], None]] = None) -> VirtualTourResult:
        """
        执行虚拟参观时序仿真
        :param params: 参观参数（朝代、日期、起止时间、步长等）
        :param progress_callback: 进度回调 callback(0.0~1.0)
        :return: 虚拟参观完整结果
        """
        dynasty_key = params.dynasty.value
        dynasty_data = self.dynasty_config.get("dynasties", {}).get(dynasty_key, {})

        calculator = LightingCalculator.from_dynasty(dynasty_key, params.grid_resolution)
        time_points = self._build_time_range(
            params.date, params.start_hour, params.end_hour, params.time_step
        )

        total = len(time_points)
        hourly_data = []
        sun_path = []

        for idx, t in enumerate(time_points):
            result = calculator.calculate_illuminance(
                t,
                sky_model_type=params.sky_model.value,
                turbidity=params.turbidity
            )
            hour_float = t.hour + t.minute / 60.0

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

            if progress_callback:
                progress_callback(min((idx + 1) / total, 1.0))

        return VirtualTourResult(
            dynasty=dynasty_key,
            dynasty_name=dynasty_data.get("name", dynasty_key),
            date=params.date,
            latitude=calculator.latitude,
            longitude=calculator.longitude,
            hourly_data=hourly_data,
            sun_path=sun_path
        )

    def get_snapshot_at(self, result: VirtualTourResult,
                        target_hour: float) -> Optional[VirtualTourHourData]:
        """
        从已有参观结果中插值获取指定时刻的快照
        :param result: 已完成的参观结果
        :param target_hour: 目标小时（支持浮点，如12.5 = 12:30）
        """
        hourly = result.hourly_data
        if not hourly:
            return None
        if target_hour <= hourly[0].hour:
            return hourly[0]
        if target_hour >= hourly[-1].hour:
            return hourly[-1]

        for i in range(len(hourly) - 1):
            if hourly[i].hour <= target_hour <= hourly[i + 1].hour:
                h0, h1 = hourly[i], hourly[i + 1]
                t = (target_hour - h0.hour) / (h1.hour - h0.hour) if h1.hour != h0.hour else 0
                return VirtualTourHourData(
                    hour=target_hour,
                    solar_altitude=h0.solar_altitude + t * (h1.solar_altitude - h0.solar_altitude),
                    solar_azimuth=self._interp_azimuth(h0.solar_azimuth, h1.solar_azimuth, t),
                    avg_illuminance=h0.avg_illuminance + t * (h1.avg_illuminance - h0.avg_illuminance),
                    min_illuminance=h0.min_illuminance + t * (h1.min_illuminance - h0.min_illuminance),
                    max_illuminance=h0.max_illuminance + t * (h1.max_illuminance - h0.max_illuminance),
                    uniformity=h0.uniformity + t * (h1.uniformity - h0.uniformity),
                    illuminance_matrix=h0.illuminance_matrix
                )
        return hourly[-1]

    @staticmethod
    def _interp_azimuth(az0: float, az1: float, t: float) -> float:
        """方位角插值（处理0°/360°跨越）"""
        diff = az1 - az0
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360
        result = az0 + t * diff
        return result % 360

    def find_sunrise_sunset(self, result: VirtualTourResult) -> Dict[str, Optional[float]]:
        """从参观结果中估算日出日落时刻"""
        sunrise = None
        sunset = None
        hourly = result.hourly_data

        prev_alt = None
        for h in hourly:
            if prev_alt is not None:
                if prev_alt <= 0 < h.solar_altitude and sunrise is None:
                    ratio = -prev_alt / (h.solar_altitude - prev_alt) if h.solar_altitude != prev_alt else 0
                    sunrise = h.hour - (1 - ratio) * (h.hour - (h.hour - 1))
                if prev_alt > 0 >= h.solar_altitude and sunset is None:
                    ratio = prev_alt / (prev_alt - h.solar_altitude) if (prev_alt - h.solar_altitude) != 0 else 0
                    sunset = prev_alt + ratio * (h.hour - (h.hour - 1))
            prev_alt = h.solar_altitude

        return {"sunrise": sunrise, "sunset": sunset}


_vr_mingtang_instance: Optional[VRMingtangTour] = None


def get_vr_mingtang_tour() -> VRMingtangTour:
    global _vr_mingtang_instance
    if _vr_mingtang_instance is None:
        _vr_mingtang_instance = VRMingtangTour()
    return _vr_mingtang_instance
