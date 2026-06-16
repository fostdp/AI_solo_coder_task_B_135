#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from enum import Enum


class SkyModelType(str, Enum):
    PEREZ = "perez"
    CIE_CLEAR = "cie_clear"
    CIE_OVERCAST = "cie_overcast"


class AlertType(str, Enum):
    LOW_SUNSHINE = "low_sunshine"


class SensorDataPoint(BaseModel):
    timestamp: Optional[datetime] = None
    hall_id: str = "han_changan_mingtang"
    location: str
    illuminance: float = Field(..., ge=0)
    solar_altitude: float = Field(..., ge=0, le=90)
    solar_azimuth: float = Field(..., ge=0, le=360)
    window_transmittance: float = Field(..., ge=0.1, le=0.95)


class SensorDataBatch(BaseModel):
    data: List[SensorDataPoint]


class SensorDataQuery(BaseModel):
    hall_id: str = "han_changan_mingtang"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    fields: Optional[List[str]] = None


class SimulationParams(BaseModel):
    date: str = Field(..., description="Simulation date in YYYY-MM-DD format")
    start_hour: int = Field(6, ge=0, le=23)
    end_hour: int = Field(18, ge=0, le=23)
    time_step: int = Field(60, ge=5, le=120, description="Time step in minutes")
    sky_model: SkyModelType = SkyModelType.PEREZ
    grid_resolution: int = Field(10, ge=5, le=30)
    latitude: float = Field(34.2658, ge=-90, le=90)
    longitude: float = Field(108.9541, ge=-180, le=180)
    turbidity: float = Field(2.5, ge=1.0, le=10.0)
    hall_id: str = "han_changan_mingtang"

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class IlluminanceMatrix(BaseModel):
    data: List[List[List[float]]]
    x: int
    y: int
    z: int


class SimulationResultData(BaseModel):
    timestamp: str
    grid_size: Dict[str, int]
    illuminance_matrix: List[List[List[float]]]
    max_illuminance: float
    min_illuminance: float
    avg_illuminance: float
    uniformity: float
    solar_altitude: float
    solar_azimuth: float


class SimulationTaskResponse(BaseModel):
    task_id: str
    status: str = "running"
    message: str = "Simulation task started"


class SimulationStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    result: Optional[List[SimulationResultData]] = None
    error: Optional[str] = None


class WindowParams(BaseModel):
    position_range: Dict[str, List[float]]
    size_range: Dict[str, List[float]]


class OptimizationParams(BaseModel):
    window_params: WindowParams
    target_uniformity: float = Field(0.7, ge=0, le=1.0)
    population_size: int = Field(30, ge=10, le=100)
    max_iterations: int = Field(50, ge=10, le=200)
    num_windows: int = Field(4, ge=1, le=8)
    hall_id: str = "han_changan_mingtang"


class WindowSolution(BaseModel):
    position: List[float]
    size: List[float]
    transmittance: float


class OptimizationResultData(BaseModel):
    best_solution: List[WindowSolution]
    best_fitness: float
    uniformity: float
    convergence_curve: List[float]
    iterations: int
    avg_illuminance: float
    execution_time: float


class OptimizationTaskResponse(BaseModel):
    task_id: str
    status: str = "running"
    message: str = "Optimization task started"


class OptimizationStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    result: Optional[OptimizationResultData] = None
    error: Optional[str] = None


class AlertConfig(BaseModel):
    min_daily_sunshine_hours: float = Field(3.0, ge=0, le=12)
    alert_season: List[str] = Field(default_factory=lambda: ["winter"])
    mqtt_topic: str = "mingtang/alerts"
    hall_id: str = "han_changan_mingtang"


class AlertRecord(BaseModel):
    id: str
    timestamp: datetime
    hall_id: str
    alert_type: AlertType
    message: str
    sunshine_hours: float
    threshold: float
    acknowledged: bool = False


class MQTTMessage(BaseModel):
    topic: str
    payload: Dict[str, Any]
    qos: int = 1


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class APIResponse(BaseModel):
    status: str = "success"
    message: str = ""
    data: Optional[Any] = None
