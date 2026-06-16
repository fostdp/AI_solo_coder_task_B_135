import { create } from 'zustand';
import type { SensorData, SimulationResult, AlertRecord, WindowSolution } from '@/types';

interface AppState {
  selectedDate: string;
  selectedHour: number;
  sensorData: SensorData[];
  latestSensorData: SensorData[];
  simulationResult: SimulationResult | null;
  simulationProgress: number;
  simulationStatus: string;
  alerts: AlertRecord[];
  optimizedWindows: WindowSolution[] | null;
  originalWindows: WindowSolution[] | null;
  showCloudMap: boolean;
  cloudMapOpacity: number;
  autoRotate: boolean;
  wireframeMode: boolean;

  setSelectedDate: (date: string) => void;
  setSelectedHour: (hour: number) => void;
  setSensorData: (data: SensorData[]) => void;
  setLatestSensorData: (data: SensorData[]) => void;
  setSimulationResult: (result: SimulationResult | null) => void;
  setSimulationProgress: (progress: number) => void;
  setSimulationStatus: (status: string) => void;
  setAlerts: (alerts: AlertRecord[]) => void;
  setOptimizedWindows: (windows: WindowSolution[] | null) => void;
  setOriginalWindows: (windows: WindowSolution[] | null) => void;
  setShowCloudMap: (show: boolean) => void;
  setCloudMapOpacity: (opacity: number) => void;
  setAutoRotate: (rotate: boolean) => void;
  setWireframeMode: (wireframe: boolean) => void;
  addAlert: (alert: AlertRecord) => void;
}

const getDefaultDate = () => {
  const today = new Date();
  today.setMonth(11);
  today.setDate(21);
  return today.toISOString().split('T')[0];
};

export const useAppStore = create<AppState>((set) => ({
  selectedDate: getDefaultDate(),
  selectedHour: 12,
  sensorData: [],
  latestSensorData: [],
  simulationResult: null,
  simulationProgress: 0,
  simulationStatus: 'idle',
  alerts: [],
  optimizedWindows: null,
  originalWindows: null,
  showCloudMap: true,
  cloudMapOpacity: 0.7,
  autoRotate: false,
  wireframeMode: false,

  setSelectedDate: (date) => set({ selectedDate: date }),
  setSelectedHour: (hour) => set({ selectedHour: hour }),
  setSensorData: (data) => set({ sensorData: data }),
  setLatestSensorData: (data) => set({ latestSensorData: data }),
  setSimulationResult: (result) => set({ simulationResult: result }),
  setSimulationProgress: (progress) => set({ simulationProgress: progress }),
  setSimulationStatus: (status) => set({ simulationStatus: status }),
  setAlerts: (alerts) => set({ alerts }),
  setOptimizedWindows: (windows) => set({ optimizedWindows: windows }),
  setOriginalWindows: (windows) => set({ originalWindows: windows }),
  setShowCloudMap: (show) => set({ showCloudMap: show }),
  setCloudMapOpacity: (opacity) => set({ cloudMapOpacity: opacity }),
  setAutoRotate: (rotate) => set({ autoRotate: rotate }),
  setWireframeMode: (wireframe) => set({ wireframeMode: wireframe }),
  addAlert: (alert) => set((state) => ({ alerts: [alert, ...state.alerts].slice(0, 100) })),
}));
