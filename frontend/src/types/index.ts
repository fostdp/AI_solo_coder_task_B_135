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

export type DynastyKey = 'han' | 'tang' | 'ming';

export interface DynastyInfo {
  key: DynastyKey;
  name: string;
  year: string;
  description: string;
  color_scheme: {
    primary: string;
    accent: string;
    roof: string;
  };
}

export interface DynastySimulationResult {
  dynasty: DynastyKey;
  dynasty_name: string;
  year: string;
  avg_illuminance: number;
  min_illuminance: number;
  max_illuminance: number;
  uniformity: number;
  grid_size: { x: number; y: number; z: number };
  illuminance_matrix: number[][][];
  solar_altitude: number;
  solar_azimuth: number;
  building_specs: {
    length: number;
    width: number;
    height: number;
    windows_count: number;
    window_transmittance: number;
  };
}

export interface StandardCompliance {
  standard_key: string;
  standard_name: string;
  country: string;
  year: number;
  dynasty: string;
  dynasty_name: string;
  simulated_metrics: Record<string, number>;
  standards_compliance: Record<string, {
    standard_value: number;
    simulated_value: number;
    compliance_ratio: number;
    pass: boolean;
  }>;
  overall_score: number;
}

export interface TreeSpecies {
  key: string;
  name: string;
  trunk_radius: number;
  canopy_radius: number;
  canopy_transmittance: number;
}

export interface TreeConfig {
  species: string;
  position: number[];
  scale: number;
}

export interface TreeImpactResult {
  without_trees: {
    avg_illuminance: number;
    min_illuminance: number;
    max_illuminance: number;
    uniformity: number;
    illuminance_matrix: number[][][];
  };
  with_trees: {
    avg_illuminance: number;
    min_illuminance: number;
    max_illuminance: number;
    uniformity: number;
    illuminance_matrix: number[][][];
  };
  illuminance_reduction_pct: number;
  uniformity_change: number;
  shaded_area_pct: number;
  tree_details: Array<{
    species: string;
    species_name: string;
    position: number[];
    canopy_radius: number;
    canopy_height: number;
    transmittance: number;
  }>;
}

export interface VirtualTourHourData {
  hour: number;
  solar_altitude: number;
  solar_azimuth: number;
  avg_illuminance: number;
  min_illuminance: number;
  max_illuminance: number;
  uniformity: number;
  illuminance_matrix?: number[][][];
}

export interface VirtualTourResult {
  dynasty: DynastyKey;
  dynasty_name: string;
  date: string;
  latitude: number;
  longitude: number;
  hourly_data: VirtualTourHourData[];
  sun_path: Array<{
    hour: number;
    altitude: number;
    azimuth: number;
  }>;
}
