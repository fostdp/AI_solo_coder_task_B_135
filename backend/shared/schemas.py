from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DynastyType(str, Enum):
    HAN = "han"
    TANG = "tang"
    MING = "ming"


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
    date: str = Field(..., description="YYYY-MM-DD")
    start_hour: int = Field(6, ge=0, le=23)
    end_hour: int = Field(18, ge=0, le=23)
    time_step: int = Field(60, ge=5, le=120)
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


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class APIResponse(BaseModel):
    status: str = "success"
    message: str = ""
    data: Optional[Any] = None


class RedisChannels:
    SENSOR_DATA = "sensor:data"
    ALERT_TRIGGERED = "alert:triggered"
    SIMULATION_REQUEST = "simulation:request"
    SIMULATION_RESULT = "simulation:result"
    OPTIMIZATION_REQUEST = "optimization:request"
    OPTIMIZATION_RESULT = "optimization:result"


class DynastyComparisonParams(BaseModel):
    dynasties: List[DynastyType] = Field(default_factory=lambda: [DynastyType.HAN, DynastyType.TANG, DynastyType.MING])
    date: str = Field(..., description="YYYY-MM-DD")
    hour: int = Field(12, ge=0, le=23)
    sky_model: SkyModelType = SkyModelType.PEREZ
    grid_resolution: int = Field(8, ge=5, le=20)
    turbidity: float = Field(2.5, ge=1.0, le=10.0)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class DynastySimulationResult(BaseModel):
    dynasty: str
    dynasty_name: str
    year: str
    avg_illuminance: float
    min_illuminance: float
    max_illuminance: float
    uniformity: float
    grid_size: Dict[str, int]
    illuminance_matrix: List[List[List[float]]]
    solar_altitude: float
    solar_azimuth: float
    building_specs: Dict[str, Any]


class StandardsComparisonResult(BaseModel):
    dynasty: str
    dynasty_name: str
    simulated_metrics: Dict[str, float]
    standards_compliance: Dict[str, Dict[str, Any]]
    overall_score: float


class TreeConfig(BaseModel):
    species: str = "pine"
    position: List[float] = Field(..., min_length=3, max_length=3)
    scale: float = Field(1.0, ge=0.1, le=3.0)


class TreeImpactParams(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    hour: int = Field(12, ge=0, le=23)
    sky_model: SkyModelType = SkyModelType.PEREZ
    grid_resolution: int = Field(8, ge=5, le=20)
    turbidity: float = Field(2.5, ge=1.0, le=10.0)
    dynasty: DynastyType = DynastyType.HAN
    trees: List[TreeConfig] = Field(default_factory=list)
    season: str = Field("summer", pattern="^(spring|summer|autumn|winter)$")

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class TreeImpactResult(BaseModel):
    without_trees: Dict[str, Any]
    with_trees: Dict[str, Any]
    illuminance_reduction_pct: float
    uniformity_change: float
    shaded_area_pct: float
    tree_details: List[Dict[str, Any]]


class VirtualTourParams(BaseModel):
    dynasty: DynastyType = DynastyType.HAN
    date: str = Field(..., description="YYYY-MM-DD")
    start_hour: int = Field(5, ge=0, le=23)
    end_hour: int = Field(19, ge=0, le=23)
    time_step: int = Field(30, ge=10, le=120)
    sky_model: SkyModelType = SkyModelType.PEREZ
    grid_resolution: int = Field(6, ge=5, le=15)
    turbidity: float = Field(2.5, ge=1.0, le=10.0)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class VirtualTourHourData(BaseModel):
    hour: float
    solar_altitude: float
    solar_azimuth: float
    avg_illuminance: float
    min_illuminance: float
    max_illuminance: float
    uniformity: float
    illuminance_matrix: Optional[List[List[List[float]]]] = None


class VirtualTourResult(BaseModel):
    dynasty: str
    dynasty_name: str
    date: str
    latitude: float
    longitude: float
    hourly_data: List[VirtualTourHourData]
    sun_path: List[Dict[str, float]]
