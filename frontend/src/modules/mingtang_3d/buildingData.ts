import type { BuildingDimensions, WindowConfig } from './types';
import type { DynastyKey } from '@/types';

export const MINGTANG_DIMENSIONS: BuildingDimensions = {
  length: 20,
  width: 20,
  height: 8,
  wallThickness: 0.5,
};

export const DEFAULT_WINDOWS: WindowConfig[] = [
  {
    position: [10, 2, 3],
    size: [2, 2],
    normal: [1, 0, 0],
    up: [0, 1, 0],
    transmittance: 0.85,
  },
  {
    position: [-10, 2, 3],
    size: [2, 2],
    normal: [-1, 0, 0],
    up: [0, 1, 0],
    transmittance: 0.85,
  },
  {
    position: [0, 2, 10],
    size: [2, 2],
    normal: [0, 0, 1],
    up: [0, 1, 0],
    transmittance: 0.85,
  },
  {
    position: [0, 2, -10],
    size: [2, 2],
    normal: [0, 0, -1],
    up: [0, 1, 0],
    transmittance: 0.85,
  },
];

export const SENSOR_LOCATIONS = [
  { name: 'main_hall', position: [0, 0, 0], label: '主殿中心' },
  { name: 'east_room', position: [8, 0, 0], label: '东室' },
  { name: 'west_room', position: [-8, 0, 0], label: '西室' },
  { name: 'south_room', position: [0, 0, 8], label: '南室' },
  { name: 'north_room', position: [0, 0, -8], label: '北室' },
  { name: 'center_altar', position: [0, 2, 0], label: '中心祭台' },
];

export const WOOD_MATERIAL = {
  color: '#8B4513',
  roughness: 0.8,
  metalness: 0.1,
};

export const WALL_MATERIAL = {
  color: '#F5E6D3',
  roughness: 0.9,
  metalness: 0,
};

export const ROOF_MATERIAL = {
  color: '#4A3728',
  roughness: 0.7,
  metalness: 0.05,
};

export const WINDOW_MATERIAL = {
  color: '#87CEEB',
  roughness: 0.1,
  metalness: 0,
  transparent: true,
  opacity: 0.6,
};

export const GOLD_DECORATION = {
  color: '#D4AF37',
  roughness: 0.3,
  metalness: 0.9,
};

export const DYNASTY_BUILDING_CONFIGS: Record<DynastyKey, {
  dimensions: BuildingDimensions;
  wallColor: string;
  roofColor: string;
  accentColor: string;
  floorColor: string;
  columnColor: string;
  windowColor: string;
  windowOpacity: number;
  roofType: 'pyramidal' | 'circular' | 'gable';
  roofHeight: number;
  label: string;
}> = {
  han: {
    dimensions: { length: 20, width: 20, height: 8, wallThickness: 0.5 },
    wallColor: '#F5E6D3',
    roofColor: '#4A3728',
    accentColor: '#D4AF37',
    floorColor: '#C4A484',
    columnColor: '#8B4513',
    windowColor: '#87CEEB',
    windowOpacity: 0.5,
    roofType: 'pyramidal',
    roofHeight: 5,
    label: '汉长安明堂',
  },
  tang: {
    dimensions: { length: 30, width: 30, height: 12, wallThickness: 0.8 },
    wallColor: '#E8D5B7',
    roofColor: '#2F4F4F',
    accentColor: '#B22222',
    floorColor: '#D4C5A9',
    columnColor: '#8B0000',
    windowColor: '#B0C4DE',
    windowOpacity: 0.45,
    roofType: 'circular',
    roofHeight: 8,
    label: '唐洛阳明堂',
  },
  ming: {
    dimensions: { length: 25, width: 18, height: 8, wallThickness: 0.6 },
    wallColor: '#8B8682',
    roofColor: '#B8860B',
    accentColor: '#DAA520',
    floorColor: '#A0937D',
    columnColor: '#6B4226',
    windowColor: '#ADD8E6',
    windowOpacity: 0.6,
    roofType: 'gable',
    roofHeight: 4,
    label: '明南京太庙',
  },
};

export const TREE_COLORS: Record<string, {
  trunk: string;
  canopy: string;
  canopyEmissive: string;
}> = {
  pine: { trunk: '#5C4033', canopy: '#1B4D1B', canopyEmissive: '#0A2E0A' },
  ginkgo: { trunk: '#6B4226', canopy: '#4A7C2E', canopyEmissive: '#2A4C1E' },
  cypress: { trunk: '#4A3728', canopy: '#1A3A1A', canopyEmissive: '#0A1A0A' },
  willow: { trunk: '#6B5B3A', canopy: '#3A6B2A', canopyEmissive: '#1A3B1A' },
  pagoda_tree: { trunk: '#5A4030', canopy: '#2A5A1A', canopyEmissive: '#1A3A0A' },
};
