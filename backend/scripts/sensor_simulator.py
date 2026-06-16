#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import logging
import random
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

import httpx
from pysolar.solar import get_altitude, get_azimuth
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


SEASON_CONFIGS = {
    "spring": {
        "name": "春季",
        "months": [3, 4, 5],
        "solar_declination_offset": 0.0,
        "cloud_cover_range": [0.2, 0.6],
        "weather_factor_range": [0.7, 1.0],
        "base_dni_multiplier": 0.9,
        "base_dif_multiplier": 1.0,
        "temperature_range": [10.0, 25.0]
    },
    "summer": {
        "name": "夏季",
        "months": [6, 7, 8],
        "solar_declination_offset": 5.0,
        "cloud_cover_range": [0.3, 0.8],
        "weather_factor_range": [0.6, 1.0],
        "base_dni_multiplier": 1.15,
        "base_dif_multiplier": 1.2,
        "temperature_range": [25.0, 38.0]
    },
    "autumn": {
        "name": "秋季",
        "months": [9, 10, 11],
        "solar_declination_offset": -2.0,
        "cloud_cover_range": [0.2, 0.5],
        "weather_factor_range": [0.75, 1.0],
        "base_dni_multiplier": 0.85,
        "base_dif_multiplier": 0.9,
        "temperature_range": [8.0, 22.0]
    },
    "winter": {
        "name": "冬季",
        "months": [12, 1, 2],
        "solar_declination_offset": -8.0,
        "cloud_cover_range": [0.4, 0.85],
        "weather_factor_range": [0.4, 0.8],
        "base_dni_multiplier": 0.6,
        "base_dif_multiplier": 0.7,
        "temperature_range": [-5.0, 10.0]
    }
}


class WindowConfig:
    def __init__(self, window_id: str, face: str, position_x: float,
                 position_y: float, width: float, height: float,
                 transmittance: float = 0.65):
        self.window_id = window_id
        self.face = face
        self.position_x = position_x
        self.position_y = position_y
        self.width = width
        self.height = height
        self.transmittance = transmittance

    @classmethod
    def from_dict(cls, data: Dict) -> "WindowConfig":
        return cls(
            window_id=data["window_id"],
            face=data.get("face", "south"),
            position_x=data.get("position_x", 0.0),
            position_y=data.get("position_y", 0.0),
            width=data.get("width", 2.0),
            height=data.get("height", 1.5),
            transmittance=data.get("transmittance", 0.65)
        )


DEFAULT_WINDOWS = [
    WindowConfig("window_south_main", "south", 0.0, 0.0, 3.0, 2.0, 0.68),
    WindowConfig("window_east_main", "east", 0.0, 0.0, 2.5, 1.8, 0.65),
    WindowConfig("window_west_main", "west", 0.0, 0.0, 2.5, 1.8, 0.65),
    WindowConfig("window_north_main", "north", 0.0, 0.0, 2.0, 1.5, 0.55)
]


class MingtangSensorSimulator:
    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        hall_id: str = "han_changan_mingtang",
        latitude: float = 34.2658,
        longitude: float = 108.9541,
        interval: int = 3600,
        season: Optional[str] = None,
        windows: Optional[List[WindowConfig]] = None
    ):
        self.api_url = api_url.rstrip('/')
        self.hall_id = hall_id
        self.latitude = latitude
        self.longitude = longitude
        self.interval = interval
        self.season = season
        self.windows = windows if windows is not None else DEFAULT_WINDOWS

        self.sensor_locations = [
            ("main_hall", 0.0, 0.0, 1.5),
            ("east_room", 8.0, 0.0, 1.5),
            ("west_room", -8.0, 0.0, 1.5),
            ("south_room", 0.0, 8.0, 1.5),
            ("north_room", 0.0, -8.0, 1.5),
            ("center_altar", 0.0, 0.0, 2.0)
        ]

        self._validate_season()

        season_cfg = SEASON_CONFIGS[self.season] if self.season else None
        self.season_name = season_cfg["name"] if season_cfg else "自动"

        logger.info(f"Initialized sensor simulator for {hall_id}")
        logger.info(f"Location: {latitude}°N, {longitude}°E")
        logger.info(f"Season: {self.season_name}")
        logger.info(f"Windows configured: {len(self.windows)}")
        for w in self.windows:
            logger.info(f"  - {w.window_id}: face={w.face}, transmittance={w.transmittance:.2f}, size={w.width}x{w.height}m")
        logger.info(f"Reporting interval: {interval}s")

    def _validate_season(self):
        if self.season is not None and self.season not in SEASON_CONFIGS:
            raise ValueError(f"Invalid season: {self.season}. "
                           f"Must be one of: {list(SEASON_CONFIGS.keys())} or None for auto")

    def _get_season_config(self, dt: datetime) -> Dict:
        if self.season:
            return SEASON_CONFIGS[self.season]
        month = dt.month
        for key, cfg in SEASON_CONFIGS.items():
            if month in cfg["months"]:
                return cfg
        return SEASON_CONFIGS["spring"]

    def calculate_solar_position(self, dt: datetime) -> Tuple[float, float]:
        try:
            altitude = get_altitude(self.latitude, self.longitude, dt)
            azimuth = get_azimuth(self.latitude, self.longitude, dt)

            season_cfg = self._get_season_config(dt)
            altitude = altitude + season_cfg["solar_declination_offset"]

            return max(0.0, altitude), azimuth
        except Exception as e:
            logger.warning(f"Error calculating solar position: {e}")
            return 0.0, 0.0

    def _get_face_window_transmittance(self, face: str) -> float:
        face_windows = [w for w in self.windows if w.face == face]
        if not face_windows:
            return 0.5
        total_area = sum(w.width * w.height for w in face_windows)
        weighted_trans = sum(w.transmittance * w.width * w.height for w in face_windows) / total_area
        return weighted_trans

    def _calculate_window_orientation_factor(
        self,
        azimuth: float,
        location_name: str
    ) -> Tuple[float, str]:
        face_map = {
            "south_room": "south",
            "east_room": "east",
            "west_room": "west",
            "north_room": "north",
            "main_hall": "south",
            "center_altar": "south"
        }
        room_face = face_map.get(location_name, "south")

        if room_face == "south":
            factor = 0.9 if 135 < azimuth < 225 else 0.4
        elif room_face == "east":
            factor = 0.9 if 45 < azimuth < 135 else 0.4
        elif room_face == "west":
            factor = 0.9 if 225 < azimuth < 315 else 0.4
        elif room_face == "north":
            factor = 0.5
        else:
            factor = 0.7

        return factor, room_face

    def calculate_illuminance(
        self,
        altitude: float,
        azimuth: float,
        location: Tuple[str, float, float, float],
        dt: datetime
    ) -> float:
        season_cfg = self._get_season_config(dt)

        if altitude <= 0:
            return random.uniform(5, 15)

        direct_normal_irradiance = 1000 * np.sin(np.radians(altitude)) * season_cfg["base_dni_multiplier"]
        diffuse_irradiance = (150 + 100 * np.sin(np.radians(altitude))) * season_cfg["base_dif_multiplier"]

        loc_name, x, y, z = location

        cloud_cover = random.uniform(*season_cfg["cloud_cover_range"])
        clear_sky_factor = 1.0 - cloud_cover * 0.6

        azimuth_rad = np.radians(azimuth)
        sun_direction = np.array([
            np.sin(azimuth_rad) * np.cos(np.radians(altitude)),
            np.cos(azimuth_rad) * np.cos(np.radians(altitude)),
            np.sin(np.radians(altitude))
        ])

        sensor_pos = np.array([x, y, z])
        distance_from_center = np.sqrt(x**2 + y**2)
        center_attenuation = max(0.3, 1.0 - distance_from_center / 20.0)

        orientation_factor, room_face = self._calculate_window_orientation_factor(azimuth, loc_name)

        room_transmittance = self._get_face_window_transmittance(room_face)

        if loc_name == "center_altar":
            center_boost = 1.1
        else:
            center_boost = 1.0

        orientation_factor_vec = max(
            0.1,
            np.dot(sun_direction[:2], np.array([x, y]) / max(1e-6, distance_from_center))
            if distance_from_center > 0 else 1.0
        )

        weather_factor = random.uniform(*season_cfg["weather_factor_range"])

        direct_component = (direct_normal_irradiance * room_transmittance
                            * orientation_factor * center_attenuation
                            * center_boost)
        diffuse_component = diffuse_irradiance * room_transmittance * 0.5

        total_illuminance = (direct_component + diffuse_component) * clear_sky_factor * weather_factor

        noise = random.gauss(0, total_illuminance * 0.05)

        return max(0.0, total_illuminance + noise)

    def generate_sensor_data(self, dt: datetime) -> List[Dict]:
        altitude, azimuth = self.calculate_solar_position(dt)
        season_cfg = self._get_season_config(dt)

        temperature = random.uniform(*season_cfg["temperature_range"])

        data_points = []

        for location in self.sensor_locations:
            loc_name, x, y, z = location

            illuminance = self.calculate_illuminance(
                altitude, azimuth, location, dt
            )

            _, room_face = self._calculate_window_orientation_factor(azimuth, loc_name)
            transmittance = self._get_face_window_transmittance(room_face)
            transmittance += random.uniform(-0.02, 0.02)
            transmittance = max(0.1, min(0.95, transmittance))

            data_point = {
                "timestamp": dt.isoformat(),
                "hall_id": self.hall_id,
                "location": loc_name,
                "illuminance": round(illuminance, 2),
                "solar_altitude": round(altitude, 4),
                "solar_azimuth": round(azimuth, 4),
                "window_transmittance": round(transmittance, 4),
                "temperature": round(temperature, 2),
                "season": self.season if self.season else self._get_season_from_month(dt.month)
            }
            data_points.append(data_point)

        return data_points

    @staticmethod
    def _get_season_from_month(month: int) -> str:
        for key, cfg in SEASON_CONFIGS.items():
            if month in cfg["months"]:
                return key
        return "spring"

    def send_data_sync(self, data: List[Dict]) -> bool:
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.api_url}/api/sensor/data",
                    json={"data": data}
                )

                if response.status_code == 200:
                    logger.info(f"Successfully sent {len(data)} data points, season={self.season_name}")
                    return True
                else:
                    logger.error(f"Failed to send data: HTTP {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error sending data: {e}")
            return False

    def generate_backfill_data(self, start_date: datetime, end_date: datetime) -> int:
        logger.info(f"Generating backfill data from {start_date} to {end_date}")
        logger.info(f"Season mode: {self.season_name}")

        total_points = 0
        current_date = start_date

        while current_date <= end_date:
            data = self.generate_sensor_data(current_date)
            if self.send_data_sync(data):
                total_points += len(data)

            current_date += timedelta(hours=1)

            if current_date.hour == 0:
                logger.info(f"Progress: {current_date.date()}, {total_points} points sent")

        logger.info(f"Backfill completed: {total_points} total points sent")
        return total_points

    def run_continuous(self):
        logger.info("Starting continuous sensor simulation...")
        logger.info(f"Season: {self.season_name}")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                now = datetime.now()
                data = self.generate_sensor_data(now)

                for point in data:
                    loc = point['location']
                    lux = point['illuminance']
                    alt = point['solar_altitude']
                    temp = point.get('temperature', 'N/A')
                    logger.debug(f"{loc}: {lux:.1f} lux, sun alt: {alt:.1f}°, temp: {temp}°C")

                self.send_data_sync(data)

                time.sleep(self.interval)

        except KeyboardInterrupt:
            logger.info("Sensor simulation stopped by user")
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            raise


def load_window_config(file_path: str) -> List[WindowConfig]:
    if not os.path.exists(file_path):
        logger.warning(f"Window config file not found: {file_path}, using defaults")
        return DEFAULT_WINDOWS

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        if isinstance(config_data, list):
            windows = [WindowConfig.from_dict(w) for w in config_data]
        elif isinstance(config_data, dict) and "windows" in config_data:
            windows = [WindowConfig.from_dict(w) for w in config_data["windows"]]
        else:
            raise ValueError("Invalid window config format")

        logger.info(f"Loaded {len(windows)} windows from config")
        return windows

    except Exception as e:
        logger.error(f"Failed to load window config: {e}, using defaults")
        return DEFAULT_WINDOWS


def create_sample_window_config(output_path: str):
    sample_config = {
        "description": "明堂窗户配置示例 - 4面墙各配置不同尺寸窗户",
        "building": "han_changan_mingtang",
        "windows": [
            {
                "window_id": "window_south_main",
                "face": "south",
                "position_x": 0.0,
                "position_y": 1.2,
                "width": 3.0,
                "height": 2.2,
                "transmittance": 0.70,
                "description": "南墙主窗"
            },
            {
                "window_id": "window_south_east",
                "face": "south",
                "position_x": -5.0,
                "position_y": 1.2,
                "width": 2.0,
                "height": 1.8,
                "transmittance": 0.65,
                "description": "南墙东窗"
            },
            {
                "window_id": "window_south_west",
                "face": "south",
                "position_x": 5.0,
                "position_y": 1.2,
                "width": 2.0,
                "height": 1.8,
                "transmittance": 0.65,
                "description": "南墙西窗"
            },
            {
                "window_id": "window_east_main",
                "face": "east",
                "position_x": 0.0,
                "position_y": 1.2,
                "width": 2.5,
                "height": 2.0,
                "transmittance": 0.62,
                "description": "东墙主窗"
            },
            {
                "window_id": "window_west_main",
                "face": "west",
                "position_x": 0.0,
                "position_y": 1.2,
                "width": 2.5,
                "height": 2.0,
                "transmittance": 0.62,
                "description": "西墙主窗"
            },
            {
                "window_id": "window_north_main",
                "face": "north",
                "position_x": 0.0,
                "position_y": 1.2,
                "width": 2.0,
                "height": 1.5,
                "transmittance": 0.50,
                "description": "北墙主窗（透光率较低）"
            }
        ]
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, ensure_ascii=False, indent=2)
    logger.info(f"Sample window config created: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Mingtang Sensor Simulator - 明堂遗址传感器模拟器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 连续模式，冬季配置
  python sensor_simulator.py --mode continuous --season winter

  # 回填7天数据，夏季配置
  python sensor_simulator.py --mode backfill --season summer --backfill-days 7

  # 使用自定义窗户配置
  python sensor_simulator.py --season spring --window-config ./windows.json

  # 生成示例窗户配置文件
  python sensor_simulator.py --generate-window-config ./windows_sample.json
        """
    )
    parser.add_argument('--mode', choices=['continuous', 'backfill'], default='continuous',
                        help='运行模式: continuous(连续上报) / backfill(回填历史数据)')
    parser.add_argument('--api-url', default='http://localhost:8000',
                        help='后端API地址(DTU服务)')
    parser.add_argument('--hall-id', default='han_changan_mingtang',
                        help='明堂建筑标识')
    parser.add_argument('--latitude', type=float, default=34.2658,
                        help='纬度(度), 西安长安约34.2658°N')
    parser.add_argument('--longitude', type=float, default=108.9541,
                        help='经度(度), 西安长安约108.9541°E')
    parser.add_argument('--interval', type=int, default=3600,
                        help='上报间隔(秒), 默认3600(1小时)')
    parser.add_argument('--backfill-days', type=int, default=7,
                        help='回填模式下回填的天数')
    parser.add_argument('--season', choices=['spring', 'summer', 'autumn', 'winter'],
                        default=None,
                        help='季节配置: spring/summer/autumn/winter, 不指定则根据日期自动判断')
    parser.add_argument('--window-config', default=None,
                        help='窗户配置JSON文件路径')
    parser.add_argument('--generate-window-config', default=None,
                        help='生成示例窗户配置文件到指定路径')

    args = parser.parse_args()

    if args.generate_window_config:
        create_sample_window_config(args.generate_window_config)
        return

    windows = None
    if args.window_config:
        windows = load_window_config(args.window_config)

    simulator = MingtangSensorSimulator(
        api_url=args.api_url,
        hall_id=args.hall_id,
        latitude=args.latitude,
        longitude=args.longitude,
        interval=args.interval,
        season=args.season,
        windows=windows
    )

    if args.mode == 'backfill':
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.backfill_days)
        simulator.generate_backfill_data(start_date, end_date)
    else:
        simulator.run_continuous()


if __name__ == "__main__":
    main()
