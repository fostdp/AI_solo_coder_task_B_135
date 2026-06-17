import axios from 'axios';
import type { SensorData, SimulationParams, SimulationStatus, AlertRecord, WindowSolution, DynastyKey, TreeConfig } from '@/types';

const dtuReceiverAPI = axios.create({
  baseURL: '/dtu/api',
  timeout: 60000,
});

const daylightSimulatorAPI = axios.create({
  baseURL: '/daylight/api',
  timeout: 120000,
});

const sunlightOptimizerAPI = axios.create({
  baseURL: '/sunlight/api',
  timeout: 60000,
});

const alarmMqttAPI = axios.create({
  baseURL: '/alarm/api',
  timeout: 60000,
});

export const sensorAPI = {
  getLatest: (hall_id: string = 'han_changan_mingtang') =>
    dtuReceiverAPI.get<SensorData[]>(`/sensor/latest`, { params: { hall_id } }),

  getData: (params: { hall_id?: string; start_time?: string; end_time?: string; location?: string; limit?: number }) =>
    dtuReceiverAPI.get<SensorData[]>('/sensor/data', { params }),

  getStatistics: (params: { hall_id?: string; start_time?: string; end_time?: string }) =>
    dtuReceiverAPI.get('/sensor/statistics', { params }),

  getSunshineHours: (params: { hall_id?: string; date?: string; threshold?: number }) =>
    dtuReceiverAPI.get('/sensor/sunshine-hours', { params }),
};

export const simulationAPI = {
  run: (params: SimulationParams) =>
    daylightSimulatorAPI.post<SimulationStatus>('/simulation/run', params),

  getStatus: (task_id: string) =>
    daylightSimulatorAPI.get<SimulationStatus>(`/simulation/status/${task_id}`),

  getTasks: () =>
    daylightSimulatorAPI.get<SimulationStatus[]>('/simulation/tasks'),

  getResult: (task_id: string) =>
    daylightSimulatorAPI.get<SimulationStatus>(`/simulation/result/${task_id}`),

  cancel: (task_id: string) =>
    daylightSimulatorAPI.post(`/simulation/cancel/${task_id}`),
};

export const optimizationAPI = {
  run: (params: {
    hall_id?: string;
    num_windows?: number;
    population_size?: number;
    max_iterations?: number;
    date?: string;
    start_hour?: number;
    end_hour?: number;
    target_uniformity?: number;
  }) =>
    sunlightOptimizerAPI.post<{ task_id: string; status: string }>('/optimization/run', params),

  getStatus: (task_id: string) =>
    sunlightOptimizerAPI.get<{
      task_id: string;
      status: string;
      progress: number;
      message: string;
      result?: {
        best_solution: WindowSolution[];
        best_fitness: number;
        uniformity: number;
        convergence_curve: number[];
        iterations: number;
        avg_illuminance: number;
      };
    }>(`/optimization/status/${task_id}`),

  getTasks: () =>
    sunlightOptimizerAPI.get('/optimization/tasks'),

  getResult: (task_id: string) =>
    sunlightOptimizerAPI.get(`/optimization/result/${task_id}`),

  compare: (original_windows?: WindowSolution[], optimized_windows?: WindowSolution[]) =>
    sunlightOptimizerAPI.post('/optimization/compare', { original_windows, optimized_windows }),
};

export const alertAPI = {
  check: (hall_id: string = 'han_changan_mingtang') =>
    alarmMqttAPI.post('/alert/check', null, { params: { hall_id } }),

  getHistory: (params?: { hall_id?: string; start_time?: string; end_time?: string; limit?: number }) =>
    alarmMqttAPI.get<AlertRecord[]>('/alert/history', { params }),

  sendTest: (hall_id: string = 'han_changan_mingtang') =>
    alarmMqttAPI.post('/alert/test', null, { params: { hall_id } }),
};

export const featureAPI = {
  getDynastyList: () =>
    daylightSimulatorAPI.get('/features/dynasty-list'),

  getDynastyConfig: (dynastyKey: DynastyKey) =>
    daylightSimulatorAPI.get(`/features/dynasty-config/${dynastyKey}`),

  runDynastyComparison: (params: {
    dynasties: DynastyKey[];
    date: string;
    hour: number;
    sky_model?: string;
    grid_resolution?: number;
    turbidity?: number;
  }) =>
    daylightSimulatorAPI.post('/features/dynasty-comparison/run', params),

  getDynastyComparisonStatus: (task_id: string) =>
    daylightSimulatorAPI.get(`/features/dynasty-comparison/status/${task_id}`),

  getStandardsComparison: (params: {
    dynasty: DynastyKey;
    avg_illuminance: number;
    min_illuminance: number;
    uniformity: number;
  }) =>
    daylightSimulatorAPI.get('/features/standards-comparison', { params }),

  getStandardsList: () =>
    daylightSimulatorAPI.get('/features/standards-list'),

  getTreeSpecies: () =>
    daylightSimulatorAPI.get('/features/tree-species'),

  runTreeImpact: (params: {
    date: string;
    hour: number;
    dynasty: DynastyKey;
    trees: TreeConfig[];
    season: string;
    sky_model?: string;
    grid_resolution?: number;
    turbidity?: number;
  }) =>
    daylightSimulatorAPI.post('/features/tree-impact/run', params),

  getTreeImpactStatus: (task_id: string) =>
    daylightSimulatorAPI.get(`/features/tree-impact/status/${task_id}`),

  runVirtualTour: (params: {
    dynasty: DynastyKey;
    date: string;
    start_hour: number;
    end_hour: number;
    time_step?: number;
    sky_model?: string;
    grid_resolution?: number;
    turbidity?: number;
  }) =>
    daylightSimulatorAPI.post('/features/virtual-tour/run', params),

  getVirtualTourStatus: (task_id: string) =>
    daylightSimulatorAPI.get(`/features/virtual-tour/status/${task_id}`),
};

export { dtuReceiverAPI, daylightSimulatorAPI, sunlightOptimizerAPI, alarmMqttAPI };
