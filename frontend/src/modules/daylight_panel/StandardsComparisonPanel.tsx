import React, { useState, useCallback } from 'react';
import { useAppStore } from '@/store';
import { featureAPI } from '@/api';
import type { DynastyKey, StandardCompliance } from '@/types';

const DYNASTY_OPTIONS: { key: DynastyKey; label: string }[] = [
  { key: 'han', label: '汉' },
  { key: 'tang', label: '唐' },
  { key: 'ming', label: '明' },
];

const STANDARD_DESCRIPTIONS: Record<string, string> = {
  gb50033_2013: '中国建筑采光设计标准，规定了居住与公共建筑的采光系数、照度及均匀度最低要求，适用于新建和改建建筑。',
  en_17037_2019: '欧洲 daylight in Buildings 标准，提供采光系数、照度水平、视野和眩光控制四方面的最低与推荐阈值。',
  lea_v4: 'LEED v4.1 日光信用项，强调通过动态采光指标（DA、UDI）和眩光控制提升室内光环境品质。',
  ancient_ideal: '基于古代礼制文献推测的明堂采光理想基准，反映古人对仪式空间光照的定性需求，无现代量化标准。',
};

const METRIC_LABELS: Record<string, string> = {
  daylight_factor_min: '采光系数最低值',
  daylight_factor_avg: '采光系数平均值',
  illuminance_min: '最低照度',
  illuminance_avg: '平均照度',
  uniformity_min: '均匀度',
  dgp_max: '眩光概率',
  da300: 'DA300',
  udi_100_3000: 'UDI 100-3000',
};

const StandardsComparisonPanel: React.FC = () => {
  const {
    selectedDynasty,
    setSelectedDynasty,
    dynastyComparisonResults,
    standardsComparisonResults,
    setStandardsComparisonResults,
  } = useAppStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getSimulationValues = useCallback(() => {
    const match = dynastyComparisonResults.find(
      (r) => r.dynasty === selectedDynasty
    );
    if (match) {
      return {
        avg_illuminance: match.avg_illuminance,
        min_illuminance: match.min_illuminance,
        uniformity: match.uniformity,
      };
    }
    return { avg_illuminance: 300, min_illuminance: 50, uniformity: 0.5 };
  }, [dynastyComparisonResults, selectedDynasty]);

  const handleCompare = useCallback(async () => {
    const values = getSimulationValues();
    setLoading(true);
    setError(null);

    try {
      const response = await featureAPI.getStandardsComparison({
        dynasty: selectedDynasty,
        avg_illuminance: values.avg_illuminance,
        min_illuminance: values.min_illuminance,
        uniformity: values.uniformity,
      });
      setStandardsComparisonResults(
        (response.data as unknown as StandardCompliance[]) ?? []
      );
    } catch (e) {
      console.error('标准对比请求失败:', e);
      setError('请求失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [selectedDynasty, getSimulationValues, setStandardsComparisonResults]);

  const scoreColor = (score: number) => {
    if (score >= 0.8) return '#4ade80';
    if (score >= 0.5) return '#D4AF37';
    return '#f87171';
  };

  const passCount = standardsComparisonResults.filter(
    (s) => s.overall_score >= 0.6
  ).length;
  const failCount = standardsComparisonResults.length - passCount;

  const passedNames = standardsComparisonResults
    .filter((s) => s.overall_score >= 0.6)
    .map((s) => s.standard_name);
  const failedNames = standardsComparisonResults
    .filter((s) => s.overall_score < 0.6)
    .map((s) => s.standard_name);

  return (
    <div className="h-full flex flex-col glass-panel overflow-hidden w-96">
      <div className="p-4 border-b border-white/10">
        <h2 className="ancient-title text-lg">跨时代采光标准对比</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="space-y-2">
          <label className="text-sm text-gray-300">选择朝代</label>
          <div className="flex gap-2">
            {DYNASTY_OPTIONS.map((opt) => (
              <label
                key={opt.key}
                className="flex-1"
              >
                <input
                  type="radio"
                  name="dynasty"
                  value={opt.key}
                  checked={selectedDynasty === opt.key}
                  onChange={() => setSelectedDynasty(opt.key)}
                  className="sr-only"
                />
                <div
                  className={`py-2 rounded text-sm font-medium text-center border transition-all cursor-pointer ${
                    selectedDynasty === opt.key
                      ? 'bg-ancient-gold/30 border-ancient-gold text-ancient-gold'
                      : 'border-white/20 text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {opt.label}
                </div>
              </label>
            ))}
          </div>
        </div>

        <button
          onClick={handleCompare}
          disabled={loading}
          className="w-full py-2.5 bg-gradient-to-r from-ancient-wood to-ancient-gold text-white rounded font-medium text-sm hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? '对比中...' : '对比现代标准'}
        </button>

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded text-xs text-red-300">
            {error}
          </div>
        )}

        {standardsComparisonResults.length > 0 && (
          <>
            <div className="space-y-3">
              {standardsComparisonResults.map((std) => {
                const pct = Math.round(std.overall_score * 100);
                const color = scoreColor(std.overall_score);
                const entries = Object.entries(std.standards_compliance);

                return (
                  <div
                    key={std.standard_key}
                    className="p-3 bg-black/30 rounded border border-white/10 space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="text-sm font-medium text-gray-100">
                          {std.standard_name}
                        </div>
                        <div className="text-xs text-gray-400">
                          {std.country} · {std.year > 0 ? std.year : `公元前${Math.abs(std.year)}年`}
                        </div>
                      </div>
                      <div
                        className="text-lg font-bold"
                        style={{ color }}
                      >
                        {pct}%
                      </div>
                    </div>

                    <div className="w-full h-2 bg-black/30 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded transition-all duration-500"
                        style={{ width: `${pct}%`, backgroundColor: color }}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                      {entries.map(([key, val]) => (
                        <div key={key} className="flex items-center gap-1.5 text-xs">
                          <span className={val.pass ? 'text-green-400' : 'text-red-400'}>
                            {val.pass ? '✓' : '✗'}
                          </span>
                          <span className="text-gray-300">{METRIC_LABELS[key] || key}</span>
                        </div>
                      ))}
                    </div>

                    {STANDARD_DESCRIPTIONS[std.standard_key] && (
                      <p className="text-xs text-gray-500 leading-relaxed pt-1 border-t border-white/5">
                        {STANDARD_DESCRIPTIONS[std.standard_key]}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="p-3 bg-ancient-wood/20 rounded border border-ancient-gold/30 space-y-2">
              <div className="text-xs text-ancient-gold font-semibold">综合评定</div>
              <div className="space-y-1 text-xs">
                {passedNames.length > 0 && (
                  <div className="flex items-start gap-1.5">
                    <span className="text-green-400">✓</span>
                    <span className="text-gray-300">
                      达标标准：{passedNames.join('、')}
                    </span>
                  </div>
                )}
                {failedNames.length > 0 && (
                  <div className="flex items-start gap-1.5">
                    <span className="text-red-400">✗</span>
                    <span className="text-gray-300">
                      未达标标准：{failedNames.join('、')}
                    </span>
                  </div>
                )}
                <div className="text-gray-400 pt-1">
                  共 {standardsComparisonResults.length} 项标准，
                  通过 {passCount} 项，未通过 {failCount} 项
                </div>
              </div>
            </div>
          </>
        )}

        <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded text-xs text-blue-200 space-y-2">
          <div className="font-semibold">标准说明</div>
          <div className="leading-relaxed">
            <p>• <span className="text-gray-200">采光系数</span>：室内某点照度与同时刻室外漫射光照度之比，反映天然光利用程度</p>
            <p>• <span className="text-gray-200">DA300</span>：一年中工作时间内照度不低于300lux的比例，衡量采光充足性</p>
            <p>• <span className="text-gray-200">UDI</span>：照度处于100-3000lux实用区间的比例，兼顾不足与过亮</p>
            <p>• <span className="text-gray-200">DGP</span>：日光眩光概率，数值越低视觉舒适度越高</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StandardsComparisonPanel;
