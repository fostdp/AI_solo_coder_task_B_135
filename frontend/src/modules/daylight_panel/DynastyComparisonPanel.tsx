import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useAppStore } from '@/store';
import { featureAPI } from '@/api';
import type { DynastyKey, DynastySimulationResult } from '@/types';

const DYNASTY_META: Record<DynastyKey, {
  label: string;
  color: string;
  accent: string;
  description: string;
}> = {
  han: {
    label: '汉',
    color: '#C4A484',
    accent: '#D4AF37',
    description: '汉长安明堂，建于西汉元始四年，方形平面，四面设窗，纸窗透光率约70%',
  },
  tang: {
    label: '唐',
    color: '#E8D5B7',
    accent: '#B22222',
    description: '唐洛阳明堂（万象神宫），武则天时期建造，体量宏大，丝质窗纱透光率约60%',
  },
  ming: {
    label: '明',
    color: '#8B8682',
    accent: '#DAA520',
    description: '明南京太庙，矩形平面，开始采用琉璃窗，透光率提升至80%',
  },
};

const DynastyComparisonPanel: React.FC = () => {
  const {
    selectedDate,
    selectedHour,
    setSelectedDate,
    setSelectedHour,
    dynastyComparisonResults,
    dynastyComparisonStatus,
    dynastyComparisonProgress,
    setDynastyComparisonResults,
    setDynastyComparisonStatus,
    setDynastyComparisonProgress,
  } = useAppStore();

  const [selectedDynasties, setSelectedDynasties] = useState<Set<DynastyKey>>(
    new Set(['han', 'tang', 'ming'])
  );
  const [skyModel, setSkyModel] = useState<'perez' | 'cie_clear' | 'cie_overcast'>('perez');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const toggleDynasty = (key: DynastyKey) => {
    setSelectedDynasties((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size > 1) next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const runComparison = useCallback(async () => {
    if (selectedDynasties.size === 0) return;

    try {
      setDynastyComparisonStatus('running');
      setDynastyComparisonProgress(0);
      setDynastyComparisonResults([]);

      const response = await featureAPI.runDynastyComparison({
        dynasties: Array.from(selectedDynasties),
        date: selectedDate,
        hour: selectedHour,
        sky_model: skyModel,
      });

      const taskId = response.data.task_id;

      if (pollRef.current) clearInterval(pollRef.current);

      pollRef.current = setInterval(async () => {
        try {
          const status = await featureAPI.getDynastyComparisonStatus(taskId);
          setDynastyComparisonProgress(status.data.progress ?? 0);

          if (status.data.status === 'completed') {
            if (pollRef.current) clearInterval(pollRef.current);
            setDynastyComparisonStatus('completed');
            setDynastyComparisonResults(
              (status.data.result as DynastySimulationResult[]) ?? []
            );
          } else if (status.data.status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current);
            setDynastyComparisonStatus('failed');
          }
        } catch (e) {
          console.error('朝代对比轮询错误:', e);
        }
      }, 2000);
    } catch (error) {
      console.error('朝代对比启动错误:', error);
      setDynastyComparisonStatus('failed');
    }
  }, [
    selectedDynasties,
    selectedDate,
    selectedHour,
    skyModel,
    setDynastyComparisonStatus,
    setDynastyComparisonProgress,
    setDynastyComparisonResults,
  ]);

  const maxIlluminance = Math.max(
    ...dynastyComparisonResults.map((r) => r.avg_illuminance),
    1
  );

  return (
    <div className="h-full flex flex-col glass-panel overflow-hidden w-96">
      <div className="p-4 border-b border-white/10">
        <h2 className="ancient-title text-lg">朝代采光对比</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="space-y-2">
          <label className="text-sm text-gray-300">选择朝代</label>
          <div className="flex gap-2">
            {(Object.keys(DYNASTY_META) as DynastyKey[]).map((key) => (
              <button
                key={key}
                onClick={() => toggleDynasty(key)}
                className="flex-1 py-2 rounded text-sm font-medium border transition-all"
                style={{
                  backgroundColor: selectedDynasties.has(key)
                    ? `${DYNASTY_META[key].color}30`
                    : 'transparent',
                  borderColor: selectedDynasties.has(key)
                    ? DYNASTY_META[key].color
                    : 'rgba(255,255,255,0.2)',
                  color: selectedDynasties.has(key)
                    ? DYNASTY_META[key].color
                    : '#9ca3af',
                }}
              >
                {DYNASTY_META[key].label}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm text-gray-300">仿真日期</label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="w-full bg-black/30 border border-white/20 rounded px-3 py-2 text-sm"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs text-gray-400">仿真时刻</label>
            <input
              type="number"
              min="0"
              max="23"
              value={selectedHour}
              onChange={(e) => setSelectedHour(parseInt(e.target.value))}
              className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-400">天空模型</label>
            <select
              value={skyModel}
              onChange={(e) => setSkyModel(e.target.value as typeof skyModel)}
              className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
            >
              <option value="perez">Perez</option>
              <option value="cie_clear">CIE 晴天</option>
              <option value="cie_overcast">CIE 阴天</option>
            </select>
          </div>
        </div>

        <button
          onClick={runComparison}
          disabled={dynastyComparisonStatus === 'running' || selectedDynasties.size === 0}
          className="w-full py-2.5 bg-gradient-to-r from-ancient-wood to-ancient-gold text-white rounded font-medium text-sm hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {dynastyComparisonStatus === 'running' ? '对比运行中...' : '运行对比'}
        </button>

        {dynastyComparisonStatus === 'running' && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-gray-400">
              <span>进度</span>
              <span>{Math.round(dynastyComparisonProgress)}%</span>
            </div>
            <div className="w-full h-2 bg-black/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-ancient-gold to-yellow-400 transition-all duration-300"
                style={{ width: `${dynastyComparisonProgress}%` }}
              />
            </div>
          </div>
        )}

        {dynastyComparisonResults.length > 0 && (
          <>
            <div className="space-y-2">
              <div className="text-xs text-ancient-gold font-semibold">对比数据</div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left py-1.5 text-gray-400 font-normal">朝代</th>
                      <th className="text-right py-1.5 text-gray-400 font-normal">年份</th>
                      <th className="text-right py-1.5 text-gray-400 font-normal">平均照度</th>
                      <th className="text-right py-1.5 text-gray-400 font-normal">均匀度</th>
                      <th className="text-right py-1.5 text-gray-400 font-normal">建筑尺寸</th>
                      <th className="text-right py-1.5 text-gray-400 font-normal">窗数</th>
                      <th className="text-right py-1.5 text-gray-400 font-normal">透光率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dynastyComparisonResults.map((r) => {
                      const meta = DYNASTY_META[r.dynasty];
                      return (
                        <tr key={r.dynasty} className="border-b border-white/5">
                          <td className="py-1.5" style={{ color: meta.color }}>
                            {meta.label}
                          </td>
                          <td className="text-right text-gray-300">{r.year}</td>
                          <td className="text-right text-gray-300">
                            {r.avg_illuminance.toFixed(0)} lx
                          </td>
                          <td className="text-right text-gray-300">
                            {(r.uniformity * 100).toFixed(1)}%
                          </td>
                          <td className="text-right text-gray-300">
                            {r.building_specs.length}×{r.building_specs.width}×{r.building_specs.height}
                          </td>
                          <td className="text-right text-gray-300">
                            {r.building_specs.windows_count}
                          </td>
                          <td className="text-right text-gray-300">
                            {(r.building_specs.window_transmittance * 100).toFixed(0)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="space-y-3">
              <div className="text-xs text-ancient-gold font-semibold">平均照度对比</div>
              <div className="space-y-2">
                {dynastyComparisonResults.map((r) => {
                  const meta = DYNASTY_META[r.dynasty];
                  const pct = (r.avg_illuminance / maxIlluminance) * 100;
                  return (
                    <div key={`ill-${r.dynasty}`} className="space-y-0.5">
                      <div className="flex justify-between text-xs">
                        <span style={{ color: meta.color }}>{meta.label}</span>
                        <span className="text-gray-400">{r.avg_illuminance.toFixed(0)} lx</span>
                      </div>
                      <div className="w-full h-4 bg-black/30 rounded overflow-hidden">
                        <div
                          className="h-full rounded transition-all duration-500"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: meta.color,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="space-y-3">
              <div className="text-xs text-ancient-gold font-semibold">均匀度对比</div>
              <div className="space-y-2">
                {dynastyComparisonResults.map((r) => {
                  const meta = DYNASTY_META[r.dynasty];
                  const pct = r.uniformity * 100;
                  return (
                    <div key={`uni-${r.dynasty}`} className="space-y-0.5">
                      <div className="flex justify-between text-xs">
                        <span style={{ color: meta.color }}>{meta.label}</span>
                        <span className="text-gray-400">{pct.toFixed(1)}%</span>
                      </div>
                      <div className="w-full h-4 bg-black/30 rounded overflow-hidden">
                        <div
                          className="h-full rounded transition-all duration-500"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: meta.accent,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-xs text-ancient-gold font-semibold">朝代简介</div>
              {dynastyComparisonResults.map((r) => {
                const meta = DYNASTY_META[r.dynasty];
                return (
                  <div
                    key={`desc-${r.dynasty}`}
                    className="p-3 rounded border"
                    style={{
                      backgroundColor: `${meta.color}15`,
                      borderColor: `${meta.color}40`,
                    }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: meta.color }}
                      />
                      <span className="text-sm font-medium" style={{ color: meta.color }}>
                        {r.dynasty_name}
                      </span>
                      <span className="text-xs text-gray-400">{r.year}</span>
                    </div>
                    <p className="text-xs text-gray-300 leading-relaxed">
                      {meta.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default DynastyComparisonPanel;
