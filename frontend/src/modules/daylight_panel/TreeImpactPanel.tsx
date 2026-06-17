import React, { useCallback, useRef, useEffect } from 'react';
import { useAppStore } from '@/store';
import { featureAPI } from '@/api';
import type { DynastyKey, TreeConfig, TreeImpactResult } from '@/types';

const SEASON_OPTIONS = [
  { key: 'spring', label: '春' },
  { key: 'summer', label: '夏' },
  { key: 'autumn', label: '秋' },
  { key: 'winter', label: '冬' },
];

const DYNASTY_OPTIONS: { key: DynastyKey; label: string }[] = [
  { key: 'han', label: '汉' },
  { key: 'tang', label: '唐' },
  { key: 'ming', label: '明' },
];

const SPECIES_LABELS: Record<string, string> = {
  pine: '古松',
  ginkgo: '银杏',
  cypress: '柏树',
  willow: '垂柳',
  pagoda_tree: '国槐',
};

const getReductionColor = (pct: number) => {
  if (pct < 10) return '#4ade80';
  if (pct <= 30) return '#facc15';
  return '#f87171';
};

const TreeImpactPanel: React.FC = () => {
  const {
    selectedDate,
    selectedHour,
    selectedDynasty,
    setSelectedDynasty,
    treeConfig,
    setTreeConfig,
    treeImpactResult,
    setTreeImpactResult,
    treeImpactStatus,
    setTreeImpactStatus,
    treeImpactProgress,
    setTreeImpactProgress,
    showTrees,
    setShowTrees,
    treeSeason,
    setTreeSeason,
  } = useAppStore();

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const addTree = useCallback(() => {
    const newTree: TreeConfig = { species: 'pine', position: [15, 15, 0], scale: 1.0 };
    setTreeConfig([...treeConfig, newTree]);
  }, [treeConfig, setTreeConfig]);

  const removeTree = useCallback(
    (index: number) => {
      setTreeConfig(treeConfig.filter((_, i) => i !== index));
    },
    [treeConfig, setTreeConfig]
  );

  const updateTreeScale = useCallback(
    (index: number, scale: number) => {
      const updated = treeConfig.map((t, i) => (i === index ? { ...t, scale } : t));
      setTreeConfig(updated);
    },
    [treeConfig, setTreeConfig]
  );

  const updateTreeSpecies = useCallback(
    (index: number, species: string) => {
      const updated = treeConfig.map((t, i) => (i === index ? { ...t, species } : t));
      setTreeConfig(updated);
    },
    [treeConfig, setTreeConfig]
  );

  const runTreeImpact = useCallback(async () => {
    try {
      setTreeImpactStatus('running');
      setTreeImpactProgress(0);
      setTreeImpactResult(null);

      const response = await featureAPI.runTreeImpact({
        date: selectedDate,
        hour: selectedHour,
        dynasty: selectedDynasty,
        trees: treeConfig,
        season: treeSeason,
      });

      const taskId = response.data.task_id;

      if (pollRef.current) clearInterval(pollRef.current);

      pollRef.current = setInterval(async () => {
        try {
          const status = await featureAPI.getTreeImpactStatus(taskId);
          setTreeImpactProgress(status.data.progress ?? 0);

          if (status.data.status === 'completed') {
            if (pollRef.current) clearInterval(pollRef.current);
            setTreeImpactStatus('completed');
            setTreeImpactResult((status.data.result as TreeImpactResult) ?? null);
          } else if (status.data.status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current);
            setTreeImpactStatus('failed');
          }
        } catch (e) {
          console.error('树木影响仿真轮询错误:', e);
        }
      }, 2000);
    } catch (error) {
      console.error('树木影响仿真启动错误:', error);
      setTreeImpactStatus('failed');
    }
  }, [
    selectedDate,
    selectedHour,
    selectedDynasty,
    treeConfig,
    treeSeason,
    setTreeImpactStatus,
    setTreeImpactProgress,
    setTreeImpactResult,
  ]);

  const result = treeImpactResult;

  return (
    <div className="h-full flex flex-col glass-panel overflow-hidden w-96">
      <div className="p-4 border-b border-white/10">
        <h2 className="ancient-title text-lg">庭院树木影响仿真</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs text-gray-400">季节</label>
            <select
              value={treeSeason}
              onChange={(e) => setTreeSeason(e.target.value)}
              className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
            >
              {SEASON_OPTIONS.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-400">朝代</label>
            <select
              value={selectedDynasty}
              onChange={(e) => setSelectedDynasty(e.target.value as DynastyKey)}
              className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
            >
              {DYNASTY_OPTIONS.map((d) => (
                <option key={d.key} value={d.key}>
                  {d.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-300">显示树木</span>
          <button
            onClick={() => setShowTrees(!showTrees)}
            className={`w-12 h-6 rounded-full transition-colors ${
              showTrees ? 'bg-ancient-gold' : 'bg-gray-600'
            }`}
          >
            <div
              className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                showTrees ? 'translate-x-6' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm text-gray-300">树木配置</label>
            <button
              onClick={addTree}
              className="px-3 py-1 bg-ancient-gold/20 border border-ancient-gold/40 text-ancient-gold rounded text-xs hover:bg-ancient-gold/30 transition"
            >
              + 添加树木
            </button>
          </div>

          <div className="space-y-2">
            {treeConfig.map((tree, idx) => (
              <div
                key={idx}
                className="p-2.5 bg-black/30 rounded border border-white/10 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <select
                    value={tree.species}
                    onChange={(e) => updateTreeSpecies(idx, e.target.value)}
                    className="bg-black/30 border border-white/20 rounded px-2 py-1 text-xs"
                  >
                    {Object.entries(SPECIES_LABELS).map(([key, name]) => (
                      <option key={key} value={key}>
                        {name}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => removeTree(idx)}
                    className="text-red-400 hover:text-red-300 text-xs transition"
                  >
                    删除
                  </button>
                </div>
                <div className="text-xs text-gray-400">
                  位置: [{tree.position.map((v) => v.toFixed(0)).join(', ')}]
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">缩放</span>
                    <span className="text-gray-300">{tree.scale.toFixed(1)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.3"
                    max="2.0"
                    step="0.1"
                    value={tree.scale}
                    onChange={(e) => updateTreeScale(idx, parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>
            ))}

            {treeConfig.length === 0 && (
              <div className="text-xs text-gray-500 text-center py-3">
                暂无树木，点击上方按钮添加
              </div>
            )}
          </div>
        </div>

        <button
          onClick={runTreeImpact}
          disabled={treeImpactStatus === 'running' || treeConfig.length === 0}
          className="w-full py-2.5 bg-gradient-to-r from-ancient-wood to-ancient-gold text-white rounded font-medium text-sm hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {treeImpactStatus === 'running' ? '仿真运行中...' : '运行树木影响仿真'}
        </button>

        {treeImpactStatus === 'running' && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-gray-400">
              <span>进度</span>
              <span>{Math.round(treeImpactProgress)}%</span>
            </div>
            <div className="w-full h-2 bg-black/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-ancient-gold to-yellow-400 transition-all duration-300"
                style={{ width: `${treeImpactProgress}%` }}
              />
            </div>
          </div>
        )}

        {result && (
          <>
            <div className="space-y-2">
              <div className="text-xs text-ancient-gold font-semibold">照度对比</div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-black/30 rounded border border-white/10 space-y-1">
                  <div className="text-xs text-gray-400">无树木</div>
                  <div className="text-lg font-bold text-gray-100">
                    {result.without_trees.avg_illuminance.toFixed(0)}{' '}
                    <span className="text-xs font-normal text-gray-400">lx</span>
                  </div>
                  <div className="text-xs text-gray-400">
                    均匀度 {(result.without_trees.uniformity * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="p-3 bg-black/30 rounded border border-white/10 space-y-1">
                  <div className="text-xs text-gray-400">有树木</div>
                  <div className="text-lg font-bold text-gray-100">
                    {result.with_trees.avg_illuminance.toFixed(0)}{' '}
                    <span className="text-xs font-normal text-gray-400">lx</span>
                  </div>
                  <div className="text-xs text-gray-400">
                    均匀度 {(result.with_trees.uniformity * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-xs text-ancient-gold font-semibold">影响指标</div>
              <div className="p-3 bg-black/30 rounded border border-white/10 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-300">照度降幅</span>
                  <span
                    className="text-sm font-bold"
                    style={{ color: getReductionColor(result.illuminance_reduction_pct) }}
                  >
                    {result.illuminance_reduction_pct.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full h-2 bg-black/30 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded transition-all duration-500"
                    style={{
                      width: `${Math.min(result.illuminance_reduction_pct, 100)}%`,
                      backgroundColor: getReductionColor(result.illuminance_reduction_pct),
                    }}
                  />
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-white/5">
                  <span className="text-xs text-gray-300">均匀度变化</span>
                  <span
                    className={`text-sm font-bold ${
                      result.uniformity_change > 0
                        ? 'text-green-400'
                        : result.uniformity_change < 0
                        ? 'text-red-400'
                        : 'text-gray-300'
                    }`}
                  >
                    {result.uniformity_change > 0 ? '+' : ''}
                    {(result.uniformity_change * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-white/5">
                  <span className="text-xs text-gray-300">遮蔽面积占比</span>
                  <span className="text-sm font-bold text-blue-300">
                    {result.shaded_area_pct.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-xs text-ancient-gold font-semibold">树木详情</div>
              <div className="space-y-2">
                {result.tree_details.map((tree, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 bg-black/30 rounded border border-white/10 space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-100">{tree.species_name}</span>
                      <span className="text-xs text-gray-400">{tree.species}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-x-3 text-xs text-gray-400">
                      <div>位置: [{tree.position.map((v) => v.toFixed(0)).join(', ')}]</div>
                      <div>树冠半径: {tree.canopy_radius.toFixed(1)}m</div>
                      <div>树冠高度: {tree.canopy_height.toFixed(1)}m</div>
                      <div>透光率: {(tree.transmittance * 100).toFixed(0)}%</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default TreeImpactPanel;
