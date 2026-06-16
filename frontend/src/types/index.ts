export interface SensorData {
  timestamp: string;
  hall_id: string;
  location: string;
  illuminance: number;
  solar_altitude: number;
  solar_azimuth: number;
  window_transmittance: number;
}

export interface SimulationParams {
  date: string;
  start_hour: number;
  end_hour: number;
  time_step: number;
  sky_model: 'perez' | 'cie_clear' | 'cie_overcast';
  grid_resolution: number;
  latitude: number;
  longitude: number;
  turbidity: number;
  hall_id: string;
}

export interface SimulationResult {
  timestamp: string;
  grid_size: { x: number; y: number; z: number };
  illuminance_matrix: number[][][];
  max_illuminance: number;
  min_illuminance: number;
  avg_illuminance: number;
  uniformity: number;
  solar_altitude: number;
  solar_azimuth: number;
}

export interface SimulationStatus {
  task_id: string;
  status: string;
  progress: number;
  result?: SimulationResult[];
  error?: string;
}

export interface WindowSolution {
  position: number[];
  size: number[];
  transmittance: number;
}

export interface OptimizationResult {
  best_solution: WindowSolution[];
  best_fitness: number;
  uniformity: number;
  convergence_curve: number[];
  iterations: number;
  avg_illuminance: number;
  execution_time: number;
}

export interface AlertRecord {
  id: string;
  timestamp: string;
  hall_id: string;
  alert_type: string;
  message: string;
  sunshine_hours: number;
  threshold: number;
  acknowledged: boolean;
}

export interface BuildingDimensions {
  length: number;
  width: number;
  height: number;
  wallThickness: number;
}

export interface WindowConfig {
  position: [number, number, number];
  size: [number, number];
  normal: [number, number, number];
  up: [number, number, number];
  transmittance: number;
}
