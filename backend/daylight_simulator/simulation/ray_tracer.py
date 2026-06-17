#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""光线追踪模块 - 从optical_params.json加载默认参数"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from abc import ABC, abstractmethod

from shared.config import load_json_config


@dataclass
class Ray:
    origin: np.ndarray
    direction: np.ndarray
    intensity: float = 1.0
    depth: int = 0

    def __post_init__(self):
        self.origin = np.array(self.origin, dtype=np.float64)
        self.direction = np.array(self.direction, dtype=np.float64)
        norm = np.linalg.norm(self.direction)
        if norm > 0:
            self.direction /= norm

    def point_at(self, t: float) -> np.ndarray:
        return self.origin + t * self.direction


@dataclass
class Intersection:
    hit: bool
    point: np.ndarray
    normal: np.ndarray
    distance: float
    material: 'Material'
    u: float = 0.0
    v: float = 0.0


@dataclass
class Material:
    name: str
    albedo: np.ndarray
    transparency: float = 0.0
    reflectivity: float = 0.0
    roughness: float = 0.5
    transmittance: float = 0.0

    def __post_init__(self):
        self.albedo = np.array(self.albedo, dtype=np.float64)

    @classmethod
    def from_config(cls, name: str, config_dict: Dict[str, Any]) -> 'Material':
        return cls(
            name=config_dict.get("name", name),
            albedo=np.array(config_dict.get("albedo", [0.5, 0.5, 0.5])),
            transparency=config_dict.get("transparency", 0.0),
            reflectivity=config_dict.get("reflectivity", 0.0),
            roughness=config_dict.get("roughness", 0.5),
            transmittance=config_dict.get("transmittance", 0.0),
        )


class Geometry(ABC):
    def __init__(self, material: Material):
        self.material = material

    @abstractmethod
    def intersect(self, ray: Ray, t_min: float = 0.001, t_max: float = 1e6) -> Intersection:
        pass

    @abstractmethod
    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        pass


class Plane(Geometry):
    def __init__(self, point: np.ndarray, normal: np.ndarray, material: Material):
        super().__init__(material)
        self.point = np.array(point, dtype=np.float64)
        self.normal = np.array(normal, dtype=np.float64)
        self.normal /= np.linalg.norm(self.normal)

    def intersect(self, ray: Ray, t_min: float = 0.001, t_max: float = 1e6) -> Intersection:
        denom = np.dot(ray.direction, self.normal)

        if abs(denom) < 1e-6:
            return Intersection(False, np.zeros(3), np.zeros(3), 0, self.material)

        t = np.dot(self.point - ray.origin, self.normal) / denom

        if t < t_min or t > t_max:
            return Intersection(False, np.zeros(3), np.zeros(3), 0, self.material)

        hit_point = ray.point_at(t)
        return Intersection(True, hit_point, self.normal, t, self.material)

    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        return np.array([-1e6, -1e6, -1e6]), np.array([1e6, 1e6, 1e6])


class Rectangle(Geometry):
    def __init__(self, center: np.ndarray, size: Tuple[float, float], normal: np.ndarray,
                 up: np.ndarray, material: Material):
        super().__init__(material)
        self.center = np.array(center, dtype=np.float64)
        self.width, self.height = size
        self.normal = np.array(normal, dtype=np.float64)
        self.normal /= np.linalg.norm(self.normal)
        self.up = np.array(up, dtype=np.float64)
        self.up -= self.up.dot(self.normal) * self.normal
        self.up /= np.linalg.norm(self.up)
        self.right = np.cross(self.normal, self.up)

    def intersect(self, ray: Ray, t_min: float = 0.001, t_max: float = 1e6) -> Intersection:
        denom = np.dot(ray.direction, self.normal)
        if abs(denom) < 1e-6:
            return Intersection(False, np.zeros(3), np.zeros(3), 0, self.material)

        t = np.dot(self.center - ray.origin, self.normal) / denom
        if t < t_min or t > t_max:
            return Intersection(False, np.zeros(3), np.zeros(3), 0, self.material)

        hit_point = ray.point_at(t)
        local = hit_point - self.center

        u = np.dot(local, self.right)
        v = np.dot(local, self.up)

        if abs(u) > self.width / 2 or abs(v) > self.height / 2:
            return Intersection(False, np.zeros(3), np.zeros(3), 0, self.material)

        u_norm = (u + self.width / 2) / self.width
        v_norm = (v + self.height / 2) / self.height

        normal = self.normal if denom < 0 else -self.normal

        return Intersection(True, hit_point, normal, t, self.material, u_norm, v_norm)

    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        half_w = self.width / 2
        half_h = self.height / 2
        corners = [
            self.center + half_w * self.right + half_h * self.up,
            self.center + half_w * self.right - half_h * self.up,
            self.center - half_w * self.right + half_h * self.up,
            self.center - half_w * self.right - half_h * self.up
        ]
        min_point = np.min(corners, axis=0)
        max_point = np.max(corners, axis=0)
        return min_point, max_point


class Box(Geometry):
    def __init__(self, min_point: np.ndarray, max_point: np.ndarray, material: Material):
        super().__init__(material)
        self.min = np.array(min_point, dtype=np.float64)
        self.max = np.array(max_point, dtype=np.float64)

    def intersect(self, ray: Ray, t_min: float = 0.001, t_max: float = 1e6) -> Intersection:
        t0 = (self.min - ray.origin) / (ray.direction + 1e-10)
        t1 = (self.max - ray.origin) / (ray.direction + 1e-10)

        t_small = np.minimum(t0, t1)
        t_big = np.maximum(t0, t1)

        t_enter = np.max(t_small)
        t_exit = np.min(t_big)

        if t_enter > t_exit or t_exit < t_min or t_enter > t_max:
            return Intersection(False, np.zeros(3), np.zeros(3), 0, self.material)

        t = t_enter if t_enter > t_min else t_exit
        if t < t_min:
            return Intersection(False, np.zeros(3), np.zeros(3), 0, self.material)

        hit_point = ray.point_at(t)

        normal = np.zeros(3)
        eps = 1e-4
        for i in range(3):
            if abs(hit_point[i] - self.min[i]) < eps:
                normal[i] = -1
            elif abs(hit_point[i] - self.max[i]) < eps:
                normal[i] = 1

        normal = normal if np.dot(normal, ray.direction) < 0 else -normal

        return Intersection(True, hit_point, normal, t, self.material)

    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        return self.min, self.max


class Cylinder(Geometry):
    def __init__(self, base_center: np.ndarray, radius: float, height: float, material: Material):
        super().__init__(material)
        self.base = np.array(base_center, dtype=np.float64)
        self.radius = radius
        self.height = height
        self.axis = np.array([0, 0, 1], dtype=np.float64)

    def intersect(self, ray: Ray, t_min: float = 0.001, t_max: float = 1e6) -> Intersection:
        d = ray.direction
        o = ray.origin - self.base

        a = d[0]**2 + d[1]**2
        b = 2 * (o[0] * d[0] + o[1] * d[1])
        c = o[0]**2 + o[1]**2 - self.radius**2

        discriminant = b**2 - 4 * a * c
        if discriminant < 0:
            return Intersection(False, np.zeros(3), np.zeros(3), 0, self.material)

        sqrt_disc = np.sqrt(discriminant)
        t0 = (-b - sqrt_disc) / (2 * a + 1e-10)
        t1 = (-b + sqrt_disc) / (2 * a + 1e-10)

        best_t = t_max
        hit_normal = np.zeros(3)
        is_side = False

        for t_cand in [t0, t1]:
            if t_cand < t_min or t_cand > t_max:
                continue
            hit_z = ray.origin[2] + t_cand * d[2]
            if self.base[2] <= hit_z <= self.base[2] + self.height:
                if t_cand < best_t:
                    best_t = t_cand
                    hit_point = ray.point_at(t_cand)
                    n = hit_point - self.base
                    hit_normal = np.array([n[0], n[1], 0])
                    norm = np.linalg.norm(hit_normal)
                    if norm > 0:
                        hit_normal /= norm
                    is_side = True

        for z_val, n_z in [(self.base[2], -1.0), (self.base[2] + self.height, 1.0)]:
            if abs(d[2]) < 1e-10:
                continue
            t_cap = (z_val - ray.origin[2]) / d[2]
            if t_cap < t_min or t_cap >= best_t:
                continue
            x_hit = ray.origin[0] + t_cap * d[0] - self.base[0]
            y_hit = ray.origin[1] + t_cap * d[1] - self.base[1]
            if x_hit**2 + y_hit**2 <= self.radius**2:
                best_t = t_cap
                hit_normal = np.array([0, 0, n_z])
                is_side = False

        if best_t >= t_max:
            return Intersection(False, np.zeros(3), np.zeros(3), 0, self.material)

        if np.dot(hit_normal, ray.direction) > 0:
            hit_normal = -hit_normal

        return Intersection(True, ray.point_at(best_t), hit_normal, best_t, self.material)

    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        r = self.radius
        return (self.base + np.array([-r, -r, 0]),
                self.base + np.array([r, r, self.height]))


class Sphere(Geometry):
    def __init__(self, center: np.ndarray, radius: float, material: Material):
        super().__init__(material)
        self.center = np.array(center, dtype=np.float64)
        self.radius = radius

    def intersect(self, ray: Ray, t_min: float = 0.001, t_max: float = 1e6) -> Intersection:
        oc = ray.origin - self.center
        a = np.dot(ray.direction, ray.direction)
        b = 2.0 * np.dot(oc, ray.direction)
        c = np.dot(oc, oc) - self.radius**2

        discriminant = b**2 - 4 * a * c
        if discriminant < 0:
            return Intersection(False, np.zeros(3), np.zeros(3), 0, self.material)

        sqrt_disc = np.sqrt(discriminant)
        t0 = (-b - sqrt_disc) / (2 * a)
        t1 = (-b + sqrt_disc) / (2 * a)

        t = t0 if t0 >= t_min else t1
        if t < t_min or t > t_max:
            return Intersection(False, np.zeros(3), np.zeros(3), 0, self.material)

        hit_point = ray.point_at(t)
        normal = (hit_point - self.center) / self.radius

        if np.dot(normal, ray.direction) > 0:
            normal = -normal

        return Intersection(True, hit_point, normal, t, self.material)

    def get_bounding_box(self) -> Tuple[np.ndarray, np.ndarray]:
        r = self.radius
        return (self.center - np.array([r, r, r]),
                self.center + np.array([r, r, r]))


class RayTracer:
    """光线追踪器 - 从optical_params.json加载默认参数"""

    _default_config: Optional[Dict[str, Any]] = None

    @classmethod
    def _get_config(cls) -> Dict[str, Any]:
        if cls._default_config is None:
            cls._default_config = load_json_config("optical_params.json")
        return cls._default_config

    def __init__(self, max_depth: Optional[int] = None, bias: Optional[float] = None):
        cfg = self._get_config().get("ray_tracer", {})
        self.max_depth = max_depth if max_depth is not None else cfg.get("max_depth", 3)
        self.bias = bias if bias is not None else cfg.get("bias", 0.001)
        self._shadow_attenuation = cfg.get("shadow_attenuation", 0.1)
        self._hemisphere_samples = cfg.get("hemisphere_samples", 8)
        self.objects: List[Geometry] = []

    def add_object(self, obj: Geometry):
        self.objects.append(obj)

    def add_objects(self, objects: List[Geometry]):
        self.objects.extend(objects)

    def clear(self):
        self.objects.clear()

    def trace_ray(self, ray: Ray, t_min: float = 0.001, t_max: float = 1e6) -> Intersection:
        closest = Intersection(False, np.zeros(3), np.zeros(3), t_max, Material('none', [0, 0, 0]))

        for obj in self.objects:
            hit = obj.intersect(ray, t_min, closest.distance)
            if hit.hit and hit.distance < closest.distance:
                closest = hit

        return closest

    def compute_illuminance(self, ray: Ray, sky_model, sun_direction: np.ndarray,
                            sun_intensity: float) -> float:
        total_illuminance = 0.0
        current_ray = ray
        current_intensity = 1.0

        for depth in range(self.max_depth):
            intersection = self.trace_ray(current_ray)

            if not intersection.hit:
                if depth == 0:
                    sky_theta = 90 - np.degrees(np.arcsin(np.clip(current_ray.direction[2], -1, 1)))
                    sky_phi = np.degrees(np.arctan2(current_ray.direction[0], current_ray.direction[1])) % 360
                    total_illuminance += sky_model.get_sky_luminance(sky_theta, sky_phi) * current_intensity
                break

            if intersection.material.transparency > 0 or intersection.material.transmittance > 0:
                transmittance = intersection.material.transmittance
                if transmittance > 0:
                    total_illuminance += self._compute_direct_illuminance(
                        intersection, sun_direction, sun_intensity, sky_model
                    ) * current_intensity * transmittance

                    new_ray = Ray(
                        intersection.point + current_ray.direction * self.bias,
                        current_ray.direction,
                        current_intensity * transmittance,
                        depth + 1
                    )
                    current_ray = new_ray
                    current_intensity *= (1 - transmittance) * intersection.material.reflectivity
                else:
                    break
            else:
                total_illuminance += self._compute_direct_illuminance(
                    intersection, sun_direction, sun_intensity, sky_model
                ) * current_intensity
                break

        return total_illuminance

    def _compute_direct_illuminance(self, intersection: Intersection, sun_direction: np.ndarray,
                                    sun_intensity: float, sky_model) -> float:
        point = intersection.point
        normal = intersection.normal

        cos_sun = np.clip(np.dot(normal, sun_direction), 0, 1)
        direct_illuminance = sun_intensity * cos_sun

        shadow_ray = Ray(
            point + normal * self.bias,
            sun_direction,
            1.0,
            0
        )
        shadow_hit = self.trace_ray(shadow_ray, t_max=1000)
        if shadow_hit.hit:
            direct_illuminance *= self._shadow_attenuation

        sky_illuminance = sky_model.get_sky_irradiance_on_surface(normal)

        total = direct_illuminance + sky_illuminance
        albedo = np.mean(intersection.material.albedo)

        return total * albedo * (1 - intersection.material.reflectivity)

    def generate_hemisphere_samples(self, normal: np.ndarray, num_samples: Optional[int] = None) -> List[np.ndarray]:
        n_samples = num_samples if num_samples is not None else self._hemisphere_samples
        samples = []
        for i in range(n_samples):
            u1 = (i + 0.5) / n_samples
            u2 = np.random.uniform(0, 1)

            r = np.sqrt(u1)
            theta = 2 * np.pi * u2

            x = r * np.cos(theta)
            y = r * np.sin(theta)
            z = np.sqrt(max(0, 1 - u1))

            tangent = np.array([1.0, 0.0, 0.0]) if abs(normal[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
            bitangent = np.cross(normal, tangent)
            bitangent /= np.linalg.norm(bitangent)
            tangent = np.cross(bitangent, normal)

            sample_dir = x * tangent + y * bitangent + z * normal
            sample_dir /= np.linalg.norm(sample_dir)
            samples.append(sample_dir)

        return samples
