import { create } from 'zustand';
import type { SensorData, SimulationResult, AlertRecord, WindowSolution, DynastyKey, DynastySimulationResult, StandardCompliance, TreeConfig, TreeImpactResult, VirtualTourResult } from '@/types';

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

  selectedDynasty: DynastyKey;
  dynastyComparisonResults: DynastySimulationResult[];
  dynastyComparisonStatus: string;
  dynastyComparisonProgress: number;

  standardsComparisonResults: StandardCompliance[];

  treeConfig: TreeConfig[];
  treeImpactResult: TreeImpactResult | null;
  treeImpactStatus: string;
  treeImpactProgress: number;
  showTrees: boolean;
  treeSeason: string;

  virtualTourResult: VirtualTourResult | null;
  virtualTourStatus: string;
  virtualTourProgress: number;
  virtualTourHour: number;
  virtualTourPlaying: boolean;
  virtualTourSpeed: number;

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

  setSelectedDynasty: (dynasty: DynastyKey) => void;
  setDynastyComparisonResults: (results: DynastySimulationResult[]) => void;
  setDynastyComparisonStatus: (status: string) => void;
  setDynastyComparisonProgress: (progress: number) => void;

  setStandardsComparisonResults: (results: StandardCompliance[]) => void;

  setTreeConfig: (trees: TreeConfig[]) => void;
  setTreeImpactResult: (result: TreeImpactResult | null) => void;
  setTreeImpactStatus: (status: string) => void;
  setTreeImpactProgress: (progress: number) => void;
  setShowTrees: (show: boolean) => void;
  setTreeSeason: (season: string) => void;

  setVirtualTourResult: (result: VirtualTourResult | null) => void;
  setVirtualTourStatus: (status: string) => void;
  setVirtualTourProgress: (progress: number) => void;
  setVirtualTourHour: (hour: number) => void;
  setVirtualTourPlaying: (playing: boolean) => void;
  setVirtualTourSpeed: (speed: number) => void;
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

  selectedDynasty: 'han',
  dynastyComparisonResults: [],
  dynastyComparisonStatus: 'idle',
  dynastyComparisonProgress: 0,

  standardsComparisonResults: [],

  treeConfig: [
    { species: 'pine', position: [12, 0, 0], scale: 1.0 },
    { species: 'pine', position: [-12, 0, 0], scale: 1.0 },
    { species: 'cypress', position: [0, 12, 0], scale: 0.9 },
    { species: 'cypress', position: [0, -12, 0], scale: 0.9 },
  ],
  treeImpactResult: null,
  treeImpactStatus: 'idle',
  treeImpactProgress: 0,
  showTrees: false,
  treeSeason: 'summer',

  virtualTourResult: null,
  virtualTourStatus: 'idle',
  virtualTourProgress: 0,
  virtualTourHour: 12,
  virtualTourPlaying: false,
  virtualTourSpeed: 1,

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

  setSelectedDynasty: (dynasty) => set({ selectedDynasty: dynasty }),
  setDynastyComparisonResults: (results) => set({ dynastyComparisonResults: results }),
  setDynastyComparisonStatus: (status) => set({ dynastyComparisonStatus: status }),
  setDynastyComparisonProgress: (progress) => set({ dynastyComparisonProgress: progress }),

  setStandardsComparisonResults: (results) => set({ standardsComparisonResults: results }),

  setTreeConfig: (trees) => set({ treeConfig: trees }),
  setTreeImpactResult: (result) => set({ treeImpactResult: result }),
  setTreeImpactStatus: (status) => set({ treeImpactStatus: status }),
  setTreeImpactProgress: (progress) => set({ treeImpactProgress: progress }),
  setShowTrees: (show) => set({ showTrees: show }),
  setTreeSeason: (season) => set({ treeSeason: season }),

  setVirtualTourResult: (result) => set({ virtualTourResult: result }),
  setVirtualTourStatus: (status) => set({ virtualTourStatus: status }),
  setVirtualTourProgress: (progress) => set({ virtualTourProgress: progress }),
  setVirtualTourHour: (hour) => set({ virtualTourHour: hour }),
  setVirtualTourPlaying: (playing) => set({ virtualTourPlaying: playing }),
  setVirtualTourSpeed: (speed) => set({ virtualTourSpeed: speed }),
}));
