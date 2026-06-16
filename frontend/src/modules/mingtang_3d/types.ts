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
