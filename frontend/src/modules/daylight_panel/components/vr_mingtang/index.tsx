import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useAppStore } from '@/store';
import { featureAPI } from '@/api';
import type { DynastyKey, VirtualTourResult, VirtualTourHourData } from '@/types';

const DYNASTY_META: Record<DynastyKey, { label: string; color: string }> = {
  han: { label: '汉', color: '#C4A484' },
  tang: { label: '唐', color: '#E8D5B7' },
  ming: { label: '明', color: '#8B8682' },
};

const SPEED_OPTIONS = [0.5, 1, 2, 4];

const formatHour = (h: number): string => {
  const hours = Math.floor(h);
  const minutes = Math.round((h - hours) * 60);
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
};

const VirtualTourPanel: React.FC = () => {
  const {
    selectedDate,
    virtualTourResult,
    virtualTourStatus,
    virtualTourProgress,
    virtualTourHour,
    virtualTourPlaying,
    virtualTourSpeed,
    setVirtualTourResult,
    setVirtualTourStatus,
    setVirtualTourProgress,
    setVirtualTourHour,
    setVirtualTourPlaying,
    setVirtualTourSpeed,
  } = useAppStore();

  const [dynasty, setDynasty] = useState<DynastyKey>('han');
  const [tourDate, setTourDate] = useState(selectedDate);
  const [startHour, setStartHour] = useState(5);
  const [endHour, setEndHour] = useState(19);
  const [timeStep, setTimeStep] = useState(30);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const playRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (playRef.current) clearInterval(playRef.current);
    };
  }, []);

  useEffect(() => {
    if (virtualTourPlaying && virtualTourResult) {
      const hourlyData = virtualTourResult.hourly_data;
      if (hourlyData.length === 0) return;

      const maxHour = hourlyData[hourlyData.length - 1].hour;
      const intervalMs = (1000 * timeStep) / (virtualTourSpeed * 60);

      playRef.current = setInterval(() => {
        const currentHour = useAppStore.getState().virtualTourHour;
        const next = currentHour + timeStep / 60;
        if (next > maxHour) {
          setVirtualTourPlaying(false);
          setVirtualTourHour(maxHour);
        } else {
          setVirtualTourHour(next);
        }
      }, intervalMs);
    }

    return () => {
      if (playRef.current) clearInterval(playRef.current);
    };
  }, [virtualTourPlaying, virtualTourSpeed, timeStep, virtualTourResult, setVirtualTourPlaying]);

  const runTour = useCallback(async () => {
    try {
      setVirtualTourStatus('running');
      setVirtualTourProgress(0);
      setVirtualTourResult(null);
      setVirtualTourPlaying(false);

      const response = await featureAPI.runVirtualTour({
        dynasty,
        date: tourDate,
        start_hour: startHour,
        end_hour: endHour,
        time_step: timeStep,
      });

      const taskId = response.data.task_id;

      if (pollRef.current) clearInterval(pollRef.current);

      pollRef.current = setInterval(async () => {
        try {
          const status = await featureAPI.getVirtualTourStatus(taskId);
          setVirtualTourProgress(status.data.progress ?? 0);

          if (status.data.status === 'completed') {
            if (pollRef.current) clearInterval(pollRef.current);
            setVirtualTourStatus('completed');
            const result = status.data.result as VirtualTourResult;
            setVirtualTourResult(result);
            if (result?.hourly_data?.length > 0) {
              setVirtualTourHour(result.hourly_data[0].hour);
            }
          } else if (status.data.status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current);
            setVirtualTourStatus('failed');
          }
        } catch (e) {
          console.error('虚拟参观轮询错误:', e);
        }
      }, 2000);
    } catch (error) {
      console.error('虚拟参观启动错误:', error);
      setVirtualTourStatus('failed');
    }
  }, [
    dynasty,
    tourDate,
    startHour,
    endHour,
    timeStep,
    setVirtualTourStatus,
    setVirtualTourProgress,
    setVirtualTourResult,
    setVirtualTourPlaying,
    setVirtualTourHour,
  ]);

  const currentHourData = virtualTourResult?.hourly_data.reduce<VirtualTourHourData | null>(
    (closest, d) => {
      if (!closest) return d;
      return Math.abs(d.hour - virtualTourHour) < Math.abs(closest.hour - virtualTourHour)
        ? d
        : closest;
    },
    null
  );

  const hourlyData = virtualTourResult?.hourly_data ?? [];
  const minHourVal = hourlyData.length > 0 ? hourlyData[0].hour : startHour;
  const maxHourVal = hourlyData.length > 0 ? hourlyData[hourlyData.length - 1].hour : endHour;

  const renderSunPath = () => {
    const sunPath = virtualTourResult?.sun_path;
    if (!sunPath || sunPath.length === 0) return null;

    const width = 280;
    const height = 120;
    const padding = 20;
    const plotW = width - padding * 2;
    const plotH = height - padding * 2;

    const hours = sunPath.map((p) => p.hour);
    const minH = Math.min(...hours);
    const maxH = Math.max(...hours);
    const maxAlt = Math.max(...sunPath.map((p) => p.altitude), 1);

    const toX = (h: number) => padding + ((h - minH) / (maxH - minH || 1)) * plotW;
    const toY = (alt: number) => padding + plotH - (alt / maxAlt) * plotH;

    const pathD = sunPath
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${toX(p.hour)} ${toY(p.altitude)}`)
      .join(' ');

    const currentSunPoint = sunPath.reduce((closest, p) => {
      if (!closest) return p;
      return Math.abs(p.hour - virtualTourHour) < Math.abs(closest.hour - virtualTourHour)
        ? p
        : closest;
    }, sunPath[0]);

    const dotX = toX(currentSunPoint.hour);
    const dotY = toY(currentSunPoint.altitude);

    return (
      <div className="space-y-1">
        <div className="text-xs text-ancient-gold font-semibold">太阳轨迹</div>
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ maxHeight: 120 }}>
          <rect x={padding} y={padding} width={plotW} height={plotH} fill="rgba(0,0,0,0.3)" rx="2" />
          <line x1={padding} y1={padding + plotH} x2={padding + plotW} y2={padding + plotH} stroke="rgba(255,255,255,0.2)" />
          <text x={padding} y={height - 4} fill="#9ca3af" fontSize="8">{minH}:00</text>
          <text x={padding + plotW - 16} y={height - 4} fill="#9ca3af" fontSize="8">{maxH}:00</text>
          <path d={pathD} fill="none" stroke="#D4AF37" strokeWidth="1.5" opacity="0.6" />
          <circle cx={dotX} cy={dotY} r="5" fill="#D4AF37" stroke="#fff" strokeWidth="1.5" />
          {currentSunPoint.altitude > 0 && (
            <line x1={dotX} y1={dotY} x2={dotX} y2={padding + plotH} stroke="#D4AF37" strokeWidth="0.5" strokeDasharray="3,3" opacity="0.4" />
          )}
        </svg>
      </div>
    );
  };

  const renderIlluminanceChart = () => {
    if (hourlyData.length === 0) return null;

    const width = 280;
    const height = 100;
    const padding = 20;
    const plotW = width - padding * 2;
    const plotH = height - padding * 2;

    const maxIll = Math.max(...hourlyData.map((d) => d.avg_illuminance), 1);

    const toX = (h: number) => padding + ((h - minHourVal) / (maxHourVal - minHourVal || 1)) * plotW;
    const toY = (v: number) => padding + plotH - (v / maxIll) * plotH;

    const lineD = hourlyData
      .map((d, i) => `${i === 0 ? 'M' : 'L'} ${toX(d.hour)} ${toY(d.avg_illuminance)}`)
      .join(' ');

    const areaD = `${lineD} L ${toX(maxHourVal)} ${padding + plotH} L ${toX(minHourVal)} ${padding + plotH} Z`;

    const cursorX = toX(virtualTourHour);

    return (
      <div className="space-y-1">
        <div className="text-xs text-ancient-gold font-semibold">照度变化</div>
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ maxHeight: 100 }}>
          <rect x={padding} y={padding} width={plotW} height={plotH} fill="rgba(0,0,0,0.3)" rx="2" />
          <path d={areaD} fill="rgba(212,175,55,0.1)" />
          <path d={lineD} fill="none" stroke="#D4AF37" strokeWidth="1.5" />
          <line x1={cursorX} y1={padding} x2={cursorX} y2={padding + plotH} stroke="#D4AF37" strokeWidth="1" strokeDasharray="3,3" opacity="0.7" />
          <text x={padding} y={padding - 4} fill="#9ca3af" fontSize="7">{maxIll.toFixed(0)} lx</text>
          <text x={padding} y={padding + plotH + 12} fill="#9ca3af" fontSize="7">{minHourVal}:00</text>
          <text x={padding + plotW - 16} y={padding + plotH + 12} fill="#9ca3af" fontSize="7">{maxHourVal}:00</text>
        </svg>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col glass-panel overflow-hidden w-96">
      <div className="p-4 border-b border-white/10">
        <h2 className="ancient-title text-lg">虚拟参观明堂</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!virtualTourResult && virtualTourStatus !== 'completed' ? (
          <>
            <div className="space-y-2">
              <label className="text-sm text-gray-300">选择朝代</label>
              <div className="flex gap-2">
                {(Object.keys(DYNASTY_META) as DynastyKey[]).map((key) => (
                  <button
                    key={key}
                    onClick={() => setDynasty(key)}
                    className="flex-1 py-2 rounded text-sm font-medium border transition-all"
                    style={{
                      backgroundColor: dynasty === key ? `${DYNASTY_META[key].color}30` : 'transparent',
                      borderColor: dynasty === key ? DYNASTY_META[key].color : 'rgba(255,255,255,0.2)',
                      color: dynasty === key ? DYNASTY_META[key].color : '#9ca3af',
                    }}
                  >
                    {DYNASTY_META[key].label}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-300">参观日期</label>
              <input
                type="date"
                value={tourDate}
                onChange={(e) => setTourDate(e.target.value)}
                className="w-full bg-black/30 border border-white/20 rounded px-3 py-2 text-sm"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-gray-400">开始时刻</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={startHour}
                  onChange={(e) => setStartHour(parseInt(e.target.value) || 0)}
                  className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-400">结束时刻</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={endHour}
                  onChange={(e) => setEndHour(parseInt(e.target.value) || 0)}
                  className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-300">时间步长（分钟）</label>
              <div className="flex gap-2">
                {[15, 30, 60].map((step) => (
                  <button
                    key={step}
                    onClick={() => setTimeStep(step)}
                    className={`flex-1 py-1.5 rounded text-sm border transition-all ${
                      timeStep === step
                        ? 'bg-ancient-gold/20 border-ancient-gold text-ancient-gold'
                        : 'border-white/20 text-gray-400 hover:border-white/40'
                    }`}
                  >
                    {step}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={runTour}
              disabled={virtualTourStatus === 'running'}
              className="w-full py-2.5 bg-gradient-to-r from-ancient-wood to-ancient-gold text-white rounded font-medium text-sm hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {virtualTourStatus === 'running' ? '参观生成中...' : '开始虚拟参观'}
            </button>

            {virtualTourStatus === 'running' && (
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-gray-400">
                  <span>进度</span>
                  <span>{Math.round(virtualTourProgress)}%</span>
                </div>
                <div className="w-full h-2 bg-black/30 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-ancient-gold to-yellow-400 transition-all duration-300"
                    style={{ width: `${virtualTourProgress}%` }}
                  />
                </div>
              </div>
            )}

            {virtualTourStatus === 'failed' && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded text-xs text-red-300">
                参观生成失败，请检查参数后重试
              </div>
            )}
          </>
        ) : (
          <>
            <div className="p-3 bg-ancient-wood/20 rounded border border-ancient-gold/30">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-ancient-gold font-semibold">
                  {virtualTourResult?.dynasty_name ?? DYNASTY_META[dynasty].label}代明堂
                </span>
                <span className="text-xs text-gray-400">{virtualTourResult?.date}</span>
              </div>
              <div className="text-xs text-gray-400">
                {virtualTourResult?.hourly_data.length ?? 0} 个时段数据
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm text-gray-300">
                  时刻: <span className="text-ancient-gold font-mono">{formatHour(virtualTourHour)}</span>
                </label>
              </div>
              <input
                type="range"
                min={minHourVal}
                max={maxHourVal}
                step={timeStep / 60}
                value={virtualTourHour}
                onChange={(e) => setVirtualTourHour(parseFloat(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>{formatHour(minHourVal)}</span>
                <span>{formatHour(maxHourVal)}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setVirtualTourPlaying(!virtualTourPlaying)}
                className="flex-1 py-2 bg-ancient-gold/20 border border-ancient-gold/40 text-ancient-gold rounded text-sm font-medium hover:bg-ancient-gold/30 transition"
              >
                {virtualTourPlaying ? '⏸ 暂停' : '▶ 播放'}
              </button>
              <div className="flex gap-1">
                {SPEED_OPTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => setVirtualTourSpeed(s)}
                    className={`px-2 py-1 rounded text-xs border transition-all ${
                      virtualTourSpeed === s
                        ? 'bg-ancient-gold/20 border-ancient-gold text-ancient-gold'
                        : 'border-white/20 text-gray-400 hover:border-white/40'
                    }`}
                  >
                    {s}x
                  </button>
                ))}
              </div>
            </div>

            {currentHourData && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-black/30 rounded border border-white/10">
                    <div className="text-xs text-gray-400 mb-1">太阳高度角</div>
                    <div className="text-lg font-mono text-ancient-gold">
                      {currentHourData.solar_altitude.toFixed(1)}°
                    </div>
                  </div>
                  <div className="p-3 bg-black/30 rounded border border-white/10">
                    <div className="text-xs text-gray-400 mb-1">太阳方位角</div>
                    <div className="text-lg font-mono text-ancient-gold">
                      {currentHourData.solar_azimuth.toFixed(1)}°
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-black/30 rounded border border-white/10 space-y-2">
                  <div className="text-xs text-ancient-gold font-semibold">当前照度</div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-gray-400">平均:</span>{' '}
                      <span className="text-gray-200">{currentHourData.avg_illuminance.toFixed(0)} lx</span>
                    </div>
                    <div>
                      <span className="text-gray-400">均匀度:</span>{' '}
                      <span className="text-gray-200">{(currentHourData.uniformity * 100).toFixed(1)}%</span>
                    </div>
                    <div>
                      <span className="text-gray-400">最小:</span>{' '}
                      <span className="text-gray-200">{currentHourData.min_illuminance.toFixed(0)} lx</span>
                    </div>
                    <div>
                      <span className="text-gray-400">最大:</span>{' '}
                      <span className="text-gray-200">{currentHourData.max_illuminance.toFixed(0)} lx</span>
                    </div>
                  </div>
                </div>
              </>
            )}

            {renderSunPath()}
            {renderIlluminanceChart()}

            <button
              onClick={() => {
                setVirtualTourResult(null);
                setVirtualTourStatus('idle');
                setVirtualTourPlaying(false);
              }}
              className="w-full py-2 border border-white/20 text-gray-400 rounded text-sm hover:border-white/40 hover:text-gray-200 transition"
            >
              重新设置参数
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default VirtualTourPanel;
