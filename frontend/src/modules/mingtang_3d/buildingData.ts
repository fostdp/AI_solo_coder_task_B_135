import type { BuildingDimensions, WindowConfig } from './types';

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
