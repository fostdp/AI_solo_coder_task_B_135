export const jetColorMap = (value: number, min: number = 0, max: number = 1000): [number, number, number, number] => {
  if (max <= min) return [0, 0, 0, 1];
  
  const normalized = Math.max(0, Math.min(1, (value - min) / (max - min)));
  
  let r: number, g: number, b: number;
  
  if (normalized < 0.125) {
    r = 0; g = 0; b = 0.5 + 4 * normalized;
  } else if (normalized < 0.375) {
    r = 0; g = 4 * (normalized - 0.125); b = 1;
  } else if (normalized < 0.625) {
    r = 4 * (normalized - 0.375); g = 1; b = 1 - 4 * (normalized - 0.375);
  } else if (normalized < 0.875) {
    r = 1; g = 1 - 4 * (normalized - 0.625); b = 0;
  } else {
    r = 1 - 4 * (normalized - 0.875); g = 0; b = 0;
  }
  
  return [
    Math.round(r * 255),
    Math.round(g * 255),
    Math.round(b * 255),
    180
  ];
};

export const jetColorMapCSS = (value: number, min: number = 0, max: number = 1000): string => {
  const [r, g, b] = jetColorMap(value, min, max);
  return `rgba(${r}, ${g}, ${b}, 0.7)`;
};

export const jetColorMapRGB = (value: number, min: number = 0, max: number = 1000): string => {
  const [r, g, b] = jetColorMap(value, min, max);
  return `rgb(${r}, ${g}, ${b})`;
};

export const generateLegendStops = (min: number, max: number, steps: number = 9) => {
  const stops = [];
  for (let i = 0; i < steps; i++) {
    const value = min + (max - min) * (i / (steps - 1));
    stops.push({
      value: Math.round(value),
      color: jetColorMapRGB(value, min, max)
    });
  }
  return stops;
};

export const formatIlluminance = (lux: number): string => {
  if (lux >= 10000) return `${(lux / 1000).toFixed(1)}k lux`;
  if (lux >= 1000) return `${lux.toFixed(0)} lux`;
  if (lux >= 100) return `${lux.toFixed(0)} lux`;
  return `${lux.toFixed(1)} lux`;
};

export const illuminanceCategory = (lux: number): { category: string; color: string } => {
  if (lux >= 10000) return { category: '极强', color: '#800000' };
  if (lux >= 5000) return { category: '很强', color: '#ff0000' };
  if (lux >= 2000) return { category: '强', color: '#ff8000' };
  if (lux >= 1000) return { category: '较强', color: '#ffff00' };
  if (lux >= 500) return { category: '适中', color: '#80ff80' };
  if (lux >= 200) return { category: '一般', color: '#00ffff' };
  if (lux >= 100) return { category: '较暗', color: '#0080ff' };
  if (lux >= 50) return { category: '暗', color: '#0000ff' };
  return { category: '极暗', color: '#000080' };
};
