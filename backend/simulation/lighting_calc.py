#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from .sky_model import SkyModelParameters, create_sky_model, SkyModel
from .ray_tracer import RayTracer, Ray, Material, Box, Rectangle, Plane
from pysolar.solar import get_altitude, get_azimuth


@dataclass
class BuildingGeometry:
    length: float = 20.0
    width: float = 20.0
    height: float = 12.0
    wall_thickness: float = 0.5

    windows: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.windows:
            self.windows = [
                {'position': [0, 10.25, 2], 'size': [2.0, 1.5], 'normal': [0, 1, 0], 'up': [0, 0, 1], 'transmittance': 0.7},
                {'position': [0, -10.25, 2], 'size': [2.0, 1.5], 'normal': [0, -1, 0], 'up': [0, 0, 1], 'transmittance': 0.7},
                {'position': [10.25, 0, 2], 'size': [2.0, 1.5], 'normal': [1, 0, 0], 'up': [0, 0, 1], 'transmittance': 0.7},
                {'position': [-10.25, 0, 2], 'size': [2.0, 1.5], 'normal': [-1, 0, 0], 'up': [0, 0, 1], 'transmittance': 0.7},
            ]


@dataclass
class IlluminanceResult:
    timestamp: datetime
    grid_size: Tuple[int, int, int]
    illuminance_matrix: np.ndarray
    max_illuminance: float
    min_illuminance: float
    avg_illuminance: float
    uniformity: float
    solar_altitude: float
    solar_azimuth: float

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'grid_size': {'x': self.grid_size[0], 'y': self.grid_size[1], 'z': self.grid_size[2]},
            'illuminance_matrix': self.illuminance_matrix.tolist(),
            'max_illuminance': float(self.max_illuminance),
            'min_illuminance': float(self.min_illuminance),
            'avg_illuminance': float(self.avg_illuminance),
            'uniformity': float(self.uniformity),
            'solar_altitude': float(self.solar_altitude),
            'solar_azimuth': float(self.solar_azimuth)
        }


class LightingCalculator:
    def __init__(
        self,
        building: BuildingGeometry,
        latitude: float,
        longitude: float,
        grid_resolution: int = 10
    ):
        self.building = building
        self.building_materials = self._create_materials()
        self.latitude = latitude
        self.longitude = longitude
        self.grid_resolution = grid_resolution

        self.ray_tracer = RayTracer(max_depth=3)
        self._build_scene()

    def _create_materials(self) -> Dict[str, Material]:
        return {
            'floor': Material(
                name='wooden_floor',
                albedo=np.array([0.6, 0.5, 0.4]),
                reflectivity=0.1,
                roughness=0.8
            ),
            'wall': Material(
                name='rammed_earth',
                albedo=np.array([0.7, 0.65, 0.55]),
                reflectivity=0.05,
                roughness=0.9
            ),
            'roof': Material(
                name='ceramic_tile',
                albedo=np.array([0.5, 0.3, 0.2]),
                reflectivity=0.05,
                roughness=0.95
            ),
            'column': Material(
                name='wooden_column',
                albedo=np.array([0.4, 0.25, 0.15]),
                reflectivity=0.1,
                roughness=0.7
            ),
            'window': Material(
                name='paper_window',
                albedo=np.array([0.9, 0.9, 0.85]),
                transmittance=0.7,
                reflectivity=0.1,
                roughness=0.3
            ),
            'ground': Material(
                name='soil',
                albedo=np.array([0.3, 0.25, 0.2]),
                reflectivity=0.1,
                roughness=0.95
            )
        }

    def _build_scene(self):
        self.ray_tracer.clear()
        b = self.building

        half_len = b.length / 2
        half_wid = b.width / 2

        floor = Plane(
            point=np.array([0, 0, 0]),
            normal=np.array([0, 0, 1]),
            material=self.building_materials['floor']
        )
        self.ray_tracer.add_object(floor)

        walls = [
            [0, half_wid, b.height/2],
            [0, -half_wid, b.height/2],
            [half_len, 0, b.height/2],
            [-half_len, 0, b.height/2],
        ]

        wall_normals = [
            [0, 1, 0], [0, -1, 0], [1, 0, 0], [-1, 0, 0]
        ]

        for center, normal in zip(walls, wall_normals):
            normal = np.array(normal)
            perp = np.array([abs(normal[1]), abs(normal[0]), 0])
            if np.all(perp == 0):
                perp = np.array([1, 0, 0])
            up = np.array([0, 0, 1])

            wall = Rectangle(
                center=np.array(center),
                size=(b.length if normal[0] == 0 else b.width, b.height),
                normal=normal,
                up=up,
                material=self.building_materials['wall']
            )
            self.ray_tracer.add_object(wall)

        roof = Plane(
            point=np.array([0, 0, b.height]),
            normal=np.array([0, 0, -1]),
            material=self.building_materials['roof']
        )
        self.ray_tracer.add_object(roof)

        for window_config in b.windows:
            window_material = Material(
                name='paper_window',
                albedo=np.array([0.9, 0.9, 0.85]),
                transmittance=window_config.get('transmittance', 0.7),
                reflectivity=0.1,
                roughness=0.3
            )
            window = Rectangle(
                center=np.array(window_config['position']),
                size=tuple(window_config['size']),
                normal=np.array(window_config['normal']),
                up=np.array(window_config['up']),
                material=window_material
            )
            self.ray_tracer.add_object(window)

        ground = Plane(
            point=np.array([0, 0, -0.01]),
            normal=np.array([0, 0, 1]),
            material=self.building_materials['ground']
        )
        self.ray_tracer.add_object(ground)

        self._add_columns()

    def _add_columns(self):
        b = self.building
        half_len = b.length / 2 - 1.5
        half_wid = b.width / 2 - 1.5

        column_material = self.building_materials['column']

        column_positions = [
            (half_len, half_wid),
            (half_len, -half_wid),
            (-half_len, half_wid),
            (-half_len, -half_wid),
            (half_len, 0),
            (-half_len, 0),
            (0, half_wid),
            (0, -half_wid),
        ]

        column_size = 0.4

        for x, y in column_positions:
            column = Box(
                min_point=np.array([x - column_size/2, y - column_size/2, 0]),
                max_point=np.array([x + column_size/2, y + column_size/2, b.height]),
                material=column_material
            )
            self.ray_tracer.add_object(column)

    def _calculate_solar_position(self, dt: datetime) -> Tuple[float, float]:
        try:
            altitude = get_altitude(self.latitude, self.longitude, dt)
            azimuth = get_azimuth(self.latitude, self.longitude, dt)
            return max(0.0, altitude), azimuth
        except Exception:
            hour_angle = (dt.hour + dt.minute/60 - 12) * 15
            declination = 23.45 * np.sin(np.radians(360 * (284 + dt.timetuple().tm_yday) / 365))
            altitude = np.degrees(np.arcsin(
                np.sin(np.radians(self.latitude)) * np.sin(np.radians(declination)) +
                np.cos(np.radians(self.latitude)) * np.cos(np.radians(declination)) * np.cos(np.radians(hour_angle))
            ))
            cos_azimuth = (np.sin(np.radians(declination)) * np.cos(np.radians(self.latitude)) -
                           np.cos(np.radians(declination)) * np.sin(np.radians(self.latitude)) * np.cos(np.radians(hour_angle))) / np.cos(np.radians(altitude))
            azimuth = np.degrees(np.arccos(np.clip(cos_azimuth, -1, 1)))
            if hour_angle > 0:
                azimuth = 360 - azimuth
            return max(0.0, altitude), azimuth

    def _get_sun_direction(self, altitude: float, azimuth: float) -> np.ndarray:
        alt_rad = np.radians(altitude)
        az_rad = np.radians(azimuth)
        return np.array([
            np.sin(az_rad) * np.cos(alt_rad),
            np.cos(az_rad) * np.cos(alt_rad),
            np.sin(alt_rad)
        ])

    def _generate_grid_points(self) -> Tuple[np.ndarray, Tuple[int, int, int]]:
        b = self.building
        half_len = b.length / 2 - b.wall_thickness
        half_wid = b.width / 2 - b.wall_thickness

        nx = ny = self.grid_resolution
        nz = max(3, self.grid_resolution // 2)

        x = np.linspace(-half_len, half_len, nx)
        y = np.linspace(-half_wid, half_wid, ny)
        z = np.linspace(0.5, b.height - 0.5, nz)

        X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
        points = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=-1)

        return points, (nx, ny, nz)

    def calculate_illuminance(
        self,
        dt: datetime,
        sky_model_type: str = 'perez',
        turbidity: float = 2.5
    ) -> IlluminanceResult:
        altitude, azimuth = self._calculate_solar_position(dt)

        if altitude <= 0:
            points, grid_size = self._generate_grid_points()
            illuminance_matrix = np.full(grid_size, 5.0)
            return IlluminanceResult(
                timestamp=dt,
                grid_size=grid_size,
                illuminance_matrix=illuminance_matrix,
                max_illuminance=5.0,
                min_illuminance=5.0,
                avg_illuminance=5.0,
                uniformity=1.0,
                solar_altitude=0.0,
                solar_azimuth=0.0
            )

        sky_params = SkyModelParameters(
            solar_altitude=altitude,
            solar_azimuth=azimuth,
            turbidity=turbidity
        )
        sky_model = create_sky_model(sky_model_type, sky_params)

        sun_direction = self._get_sun_direction(altitude, azimuth)
        sun_intensity = sky_model.get_direct_irradiance()

        points, grid_size = self._generate_grid_points()
        illuminance_values = []

        for point in points:
            hemisphere_samples = self.ray_tracer.generate_hemisphere_samples(
                np.array([0, 0, 1]), num_samples=8)

            total_illuminance = 0.0

            for sample_dir in hemisphere_samples:
                ray = Ray(
                    origin=point + np.array([0, 0, 0.01]),
                    direction=sample_dir,
                    intensity=1.0,
                    depth=0
                )
                illuminance = self.ray_tracer.compute_illuminance(
                    ray, sky_model, sun_direction, sun_intensity)
                total_illuminance += illuminance

            avg_illuminance = total_illuminance / len(hemisphere_samples)
            illuminance_values.append(avg_illuminance)

        illuminance_matrix = np.array(illuminance_values).reshape(grid_size)

        max_ill = float(np.max(illuminance_matrix))
        min_ill = float(np.min(illuminance_matrix))
        avg_ill = float(np.mean(illuminance_matrix))
        uniformity = min_ill / avg_ill if avg_ill > 0 else 0

        return IlluminanceResult(
            timestamp=dt,
            grid_size=grid_size,
            illuminance_matrix=illuminance_matrix,
            max_illuminance=max_ill,
            min_illuminance=min_ill,
            avg_illuminance=avg_ill,
            uniformity=uniformity,
            solar_altitude=altitude,
            solar_azimuth=azimuth
        )

    def calculate_hourly(
        self,
        date: datetime,
        start_hour: int = 6,
        end_hour: int = 18,
        time_step: int = 60,
        sky_model_type: str = 'perez'
    ) -> List[IlluminanceResult]:
        results = []
        current_time = datetime(date.year, date.month, date.day, start_hour)
        end_time = datetime(date.year, date.month, date.day, end_hour)

        while current_time <= end_time:
            result = self.calculate_illuminance(current_time, sky_model_type)
            results.append(result)
            current_time += timedelta(minutes=time_step)

        return results

    def calculate_daily_sunshine_hours(self, date: datetime) -> float:
        sunrise = datetime(date.year, date.month, date.day, 6)
        sunset = datetime(date.year, date.month, date.day, 18)

        sunshine_hours = 0.0
        current = sunrise

        while current <= sunset:
            altitude, _ = self._calculate_solar_position(current)
            if altitude > 0:
                sunshine_hours += 1
            current += timedelta(hours=1)

        return sunshine_hours

    def update_windows(self, windows: List[Dict]):
        self.building.windows = windows
        self._build_scene()
