import React, { useRef, useEffect, useMemo, useState, useCallback } from 'react';
import { useAppStore } from '@/store';
import { jetColorMap, formatIlluminance, generateLegendStops, illuminanceCategory } from './colorMap';
import type { SimulationResult } from '@/types';

interface LightCloudMapProps {
  simulationResult: SimulationResult | null;
  width: number;
  height: number;
}

const isMobile = (): boolean => {
  if (typeof window === 'undefined') return false;
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
    || window.innerWidth < 768;
};

const buildColorLUT = (minVal: number, maxVal: number, steps: number = 256): Uint8ClampedArray => {
  const lut = new Uint8ClampedArray(steps * 4);
  for (let i = 0; i < steps; i++) {
    const value = minVal + (maxVal - minVal) * (i / (steps - 1));
    const [r, g, b, a] = jetColorMap(value, minVal, maxVal);
    lut[i * 4] = r;
    lut[i * 4 + 1] = g;
    lut[i * 4 + 2] = b;
    lut[i * 4 + 3] = a;
  }
  return lut;
};

const LightCloudMap: React.FC<LightCloudMapProps> = ({
  simulationResult,
  width,
  height
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const offscreenCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number>(0);
  const pendingRedrawRef = useRef<boolean>(false);
  const lastDataKeyRef = useRef<string>('');

  const { cloudMapOpacity, showCloudMap, selectedHour } = useAppStore();
  const [isMobileDevice, setIsMobileDevice] = useState(false);
  const [renderScale, setRenderScale] = useState(1);

  useEffect(() => {
    const mobile = isMobile();
    setIsMobileDevice(mobile);
    setRenderScale(mobile ? 0.5 : 1);
  }, []);

  const renderWidth = Math.floor(width * renderScale);
  const renderHeight = Math.floor(height * renderScale);

  const stats = useMemo(() => {
    if (!simulationResult) return null;
    return {
      max: simulationResult.max_illuminance,
      min: simulationResult.min_illuminance,
      avg: simulationResult.avg_illuminance,
      uniformity: simulationResult.uniformity,
      category: illuminanceCategory(simulationResult.avg_illuminance)
    };
  }, [simulationResult]);

  const getDataKey = useCallback((): string => {
    if (!simulationResult) return '';
    return `${simulationResult.timestamp}_${simulationResult.max_illuminance}_${simulationResult.min_illuminance}_${renderScale}`;
  }, [simulationResult, renderScale]);

  const renderCloudMapData = useCallback((
    ctx: CanvasRenderingContext2D,
    result: SimulationResult,
    mapX: number,
    mapY: number,
    mapW: number,
    mapH: number,
    opacity: number
  ) => {
    const { grid_size, illuminance_matrix, max_illuminance, min_illuminance } = result;
    const nx = grid_size.x;
    const nz = grid_size.z;
    const ySlice = Math.floor(grid_size.y / 2);

    const cellW = mapW / nx;
    const cellH = mapH / nz;

    const useLowQuality = isMobileDevice || renderScale < 1;
    const step = useLowQuality ? Math.max(1, Math.floor(nx / 30)) : 1;

    const colorLUT = buildColorLUT(min_illuminance, max_illuminance, 256);
    const valueRange = max_illuminance - min_illuminance;

    if (useLowQuality && valueRange > 0) {
      const imgW = Math.ceil(nx / step);
      const imgH = Math.ceil(nz / step);
      const imageData = ctx.createImageData(imgW, imgH);
      const data = imageData.data;

      let idx = 0;
      for (let j = 0; j < nz; j += step) {
        for (let i = 0; i < nx; i += step) {
          const illuminance = illuminance_matrix[i][ySlice][j];

          if (isNaN(illuminance) || illuminance < 0) {
            data[idx] = 0;
            data[idx + 1] = 0;
            data[idx + 2] = 0;
            data[idx + 3] = 0;
          } else {
            const normalized = Math.max(0, Math.min(1, (illuminance - min_illuminance) / valueRange));
            const lutIdx = Math.min(255, Math.floor(normalized * 255)) * 4;
            data[idx] = colorLUT[lutIdx];
            data[idx + 1] = colorLUT[lutIdx + 1];
            data[idx + 2] = colorLUT[lutIdx + 2];
            data[idx + 3] = Math.floor(colorLUT[lutIdx + 3] * opacity);
          }
          idx += 4;
        }
      }

      const tmpCanvas = document.createElement('canvas');
      tmpCanvas.width = imgW;
      tmpCanvas.height = imgH;
      const tmpCtx = tmpCanvas.getContext('2d')!;
      tmpCtx.putImageData(imageData, 0, 0);

      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'low';
      ctx.drawImage(tmpCanvas, mapX, mapY, mapW, mapH);
    } else {
      for (let j = 0; j < nz; j++) {
        for (let i = 0; i < nx; i++) {
          const illuminance = illuminance_matrix[i][ySlice][j];

          if (isNaN(illuminance) || illuminance < 0) continue;

          const normalized = Math.max(0, Math.min(1, (illuminance - min_illuminance) / valueRange));
          const lutIdx = Math.min(255, Math.floor(normalized * 255)) * 4;

          const r = colorLUT[lutIdx];
          const g = colorLUT[lutIdx + 1];
          const b = colorLUT[lutIdx + 2];
          const a = (colorLUT[lutIdx + 3] / 255) * opacity;

          ctx.fillStyle = `rgba(${r},${g},${b},${a})`;
          ctx.fillRect(
            mapX + i * cellW,
            mapY + j * cellH,
            cellW + 0.5,
            cellH + 0.5
          );
        }
      }
    }
  }, [isMobileDevice, renderScale]);

  const drawOverlay = useCallback((
    ctx: CanvasRenderingContext2D,
    result: SimulationResult,
    padding: number,
    mapWidth: number,
    mapHeight: number,
    hour: number
  ) => {
    const { min_illuminance, max_illuminance, avg_illuminance, uniformity } = result;

    ctx.strokeStyle = 'rgba(212, 175, 55, 0.6)';
    ctx.lineWidth = 2;
    ctx.strokeRect(padding, padding, mapWidth, mapHeight);

    ctx.fillStyle = '#D4AF37';
    ctx.font = 'bold 14px "Noto Serif SC", serif';
    ctx.textAlign = 'center';
    ctx.fillText('室内采光伪彩色云图（俯视切面 y=1.5m）', width / 2, 30);

    ctx.fillStyle = '#e8e8e8';
    ctx.font = '12px "Noto Serif SC", serif';
    ctx.textAlign = 'left';
    ctx.fillText('北', padding + mapWidth / 2, padding - 15);
    ctx.textAlign = 'right';
    ctx.fillText('南', padding + mapWidth / 2, padding + mapHeight + 30);
    ctx.textAlign = 'left';
    ctx.fillText('西', padding - 30, padding + mapHeight / 2 + 5);
    ctx.textAlign = 'right';
    ctx.fillText('东', padding + mapWidth + 30, padding + mapHeight / 2 + 5);

    const legendX = padding;
    const legendY = height - 40;
    const legendWidth = mapWidth;
    const legendHeight = 15;

    const gradient = ctx.createLinearGradient(legendX, 0, legendX + legendWidth, 0);
    const stops = generateLegendStops(min_illuminance, max_illuminance);
    stops.forEach((stop, idx) => {
      gradient.addColorStop(idx / (stops.length - 1), stop.color);
    });

    ctx.fillStyle = gradient;
    ctx.fillRect(legendX, legendY, legendWidth, legendHeight);

    ctx.strokeStyle = 'rgba(212, 175, 55, 0.8)';
    ctx.lineWidth = 1;
    ctx.strokeRect(legendX, legendY, legendWidth, legendHeight);

    ctx.fillStyle = '#e8e8e8';
    ctx.font = '10px "Noto Serif SC", serif';
    ctx.textAlign = 'center';
    stops.forEach((stop, idx) => {
      const x = legendX + (idx / (stops.length - 1)) * legendWidth;
      ctx.fillText(formatIlluminance(stop.value), x, legendY + legendHeight + 15);
      ctx.beginPath();
      ctx.moveTo(x, legendY);
      ctx.lineTo(x, legendY - 5);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.stroke();
    });

    const category = illuminanceCategory(avg_illuminance);

    ctx.fillStyle = '#e8e8e8';
    ctx.font = '11px "Noto Serif SC", serif';
    ctx.textAlign = 'left';
    ctx.fillText(`平均照度: ${formatIlluminance(avg_illuminance)} (${category.category})`, padding, height - 60);
    ctx.fillText(`采光均匀度: ${(uniformity * 100).toFixed(1)}%`, padding, height - 45);

    ctx.fillStyle = '#D4AF37';
    ctx.font = 'bold 12px "Noto Serif SC", serif';
    ctx.textAlign = 'right';
    ctx.fillText(`${hour.toString().padStart(2, '0')}:00`, width - padding, 30);
  }, [width, height]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    if (!showCloudMap || !simulationResult) {
      lastDataKeyRef.current = '';
      return;
    }

    const padding = 60;
    const mapWidth = width - padding * 2;
    const mapHeight = height - padding * 2;

    const currentDataKey = getDataKey();

    if (currentDataKey !== lastDataKeyRef.current || !offscreenCanvasRef.current) {
      if (!offscreenCanvasRef.current) {
        offscreenCanvasRef.current = document.createElement('canvas');
      }
      const offCanvas = offscreenCanvasRef.current;
      offCanvas.width = width;
      offCanvas.height = height;
      const offCtx = offCanvas.getContext('2d');

      if (offCtx) {
        offCtx.clearRect(0, 0, width, height);
        renderCloudMapData(offCtx, simulationResult, padding, padding, mapWidth, mapHeight, 1);
      }
      lastDataKeyRef.current = currentDataKey;
    }

    ctx.save();
    ctx.globalAlpha = cloudMapOpacity;
    if (offscreenCanvasRef.current) {
      ctx.drawImage(offscreenCanvasRef.current, 0, 0);
    }
    ctx.restore();

    drawOverlay(ctx, simulationResult, padding, mapWidth, mapHeight, selectedHour);

    pendingRedrawRef.current = false;
  }, [simulationResult, width, height, cloudMapOpacity, showCloudMap, selectedHour, getDataKey, renderCloudMapData, drawOverlay]);

  const scheduleRedraw = useCallback(() => {
    if (pendingRedrawRef.current) return;
    pendingRedrawRef.current = true;

    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
    }

    animFrameRef.current = requestAnimationFrame(() => {
      draw();
    });
  }, [draw]);

  useEffect(() => {
    scheduleRedraw();
  }, [scheduleRedraw]);

  useEffect(() => {
    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, []);

  return (
    <div className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{
          display: showCloudMap ? 'block' : 'none',
          imageRendering: isMobileDevice ? 'auto' : 'crisp-edges'
        }}
      />

      {!simulationResult && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center p-6 glass-panel">
            <div className="text-4xl mb-3">☀️</div>
            <p className="text-gray-400 text-sm">运行采光仿真后显示伪彩色云图</p>
            <p className="text-gray-500 text-xs mt-2">请在右侧面板点击"运行仿真"</p>
          </div>
        </div>
      )}

      {stats && (
        <div className="absolute top-4 right-4 glass-panel p-3 text-xs space-y-1">
          <div className="font-semibold text-ancient-gold mb-2">当前时段数据</div>
          <div className="flex justify-between">
            <span className="text-gray-400">最大:</span>
            <span style={{ color: illuminanceCategory(stats.max).color }}>
              {formatIlluminance(stats.max)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">最小:</span>
            <span style={{ color: illuminanceCategory(stats.min).color }}>
              {formatIlluminance(stats.min)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">平均:</span>
            <span style={{ color: stats.category.color }}>
              {formatIlluminance(stats.avg)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">均匀度:</span>
            <span className={stats.uniformity > 0.7 ? 'text-sensor-good' : stats.uniformity > 0.5 ? 'text-sensor-warning' : 'text-sensor-danger'}>
              {(stats.uniformity * 100).toFixed(1)}%
            </span>
          </div>
          {isMobileDevice && (
            <div className="pt-1 mt-1 border-t border-white/10 text-[10px] text-gray-500">
              性能模式 (50%分辨率)
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LightCloudMap;
