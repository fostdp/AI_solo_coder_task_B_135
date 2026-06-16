import React, { useState, useCallback } from 'react';
import { useAppStore } from '@/store';
import { simulationAPI, optimizationAPI, alertAPI } from '@/api';
import { formatIlluminance } from './colorMap';
import type { SimulationParams, SimulationResult } from '@/types';

const ControlPanel: React.FC = () => {
  const {
    selectedDate,
    selectedHour,
    setSelectedDate,
    setSelectedHour,
    setSimulationResult,
    setSimulationProgress,
    setSimulationStatus,
    simulationProgress,
    simulationStatus,
    showCloudMap,
    setShowCloudMap,
    cloudMapOpacity,
    setCloudMapOpacity,
    autoRotate,
    setAutoRotate,
    wireframeMode,
    setWireframeMode,
    simulationResult
  } = useAppStore();

  const [skyModel, setSkyModel] = useState<'perez' | 'cie_clear' | 'cie_overcast'>('perez');
  const [gridResolution, setGridResolution] = useState(10);
  const [turbidity, setTurbidity] = useState(2.5);
  const [startHour, setStartHour] = useState(6);
  const [endHour, setEndHour] = useState(18);

  const [optimizationParams, setOptimizationParams] = useState({
    num_windows: 4,
    population_size: 30,
    max_iterations: 50,
    target_uniformity: 0.8
  });

  const [optimizationStatus, setOptimizationStatus] = useState<string>('idle');
  const [optimizationProgress, setOptimizationProgress] = useState(0);
  const [optimizationResult, setOptimizationResult] = useState<any>(null);

  const [activeTab, setActiveTab] = useState<'simulation' | 'optimization' | 'alert' | 'display'>('simulation');

  const runSimulation = useCallback(async () => {
    try {
      setSimulationStatus('running');
      setSimulationProgress(0);

      const params: SimulationParams = {
        date: selectedDate,
        start_hour: startHour,
        end_hour: endHour,
        time_step: 60,
        sky_model: skyModel,
        grid_resolution: gridResolution,
        latitude: 34.265,
        longitude: 108.954,
        turbidity: turbidity,
        hall_id: 'han_changan_mingtang'
      };

      const response = await simulationAPI.run(params);
      const taskId = response.data.task_id;

      const pollInterval = setInterval(async () => {
        try {
          const status = await simulationAPI.getStatus(taskId);
          setSimulationProgress(status.data.progress);

          if (status.data.status === 'completed') {
            clearInterval(pollInterval);
            setSimulationStatus('completed');
            const results = status.data.result || [];

            if (results.length > 0) {
              const hourIndex = Math.min(
                Math.max(selectedHour - startHour, 0),
                results.length - 1
              );
              setSimulationResult(results[hourIndex] as SimulationResult);
            }
          } else if (status.data.status === 'failed') {
            clearInterval(pollInterval);
            setSimulationStatus('failed');
          }
        } catch (e) {
          console.error('Polling error:', e);
        }
      }, 2000);

    } catch (error) {
      console.error('Simulation error:', error);
      setSimulationStatus('failed');
    }
  }, [selectedDate, startHour, endHour, skyModel, gridResolution, turbidity, selectedHour, setSimulationStatus, setSimulationProgress, setSimulationResult]);

  const runOptimization = useCallback(async () => {
    try {
      setOptimizationStatus('running');
      setOptimizationProgress(0);

      const response = await optimizationAPI.run({
        date: selectedDate,
        start_hour: startHour,
        end_hour: endHour,
        ...optimizationParams
      });

      const taskId = response.data.task_id;

      const pollInterval = setInterval(async () => {
        try {
          const status = await optimizationAPI.getStatus(taskId);
          setOptimizationProgress(status.data.progress);

          if (status.data.status === 'completed') {
            clearInterval(pollInterval);
            setOptimizationStatus('completed');
            setOptimizationResult(status.data.result);
          } else if (status.data.status === 'failed') {
            clearInterval(pollInterval);
            setOptimizationStatus('failed');
          }
        } catch (e) {
          console.error('Polling error:', e);
        }
      }, 2000);

    } catch (error) {
      console.error('Optimization error:', error);
      setOptimizationStatus('failed');
    }
  }, [selectedDate, startHour, endHour, optimizationParams]);

  const handleHourChange = (hour: number) => {
    setSelectedHour(hour);
    if (simulationStatus === 'completed' && simulationResult) {
      // 如果有完整的日仿真数据，这里可以切换不同时段的结果
    }
  };

  return (
    <div className="h-full flex flex-col glass-panel overflow-hidden">
      <div className="p-4 border-b border-white/10">
        <h2 className="ancient-title text-lg">控制面板</h2>
      </div>

      <div className="flex border-b border-white/10">
        {[
          { key: 'simulation', label: '采光仿真' },
          { key: 'optimization', label: '日照优化' },
          { key: 'alert', label: '告警管理' },
          { key: 'display', label: '显示设置' }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`flex-1 py-2 text-xs transition-colors ${
              activeTab === tab.key
                ? 'bg-ancient-wood/30 text-ancient-gold border-b-2 border-ancient-gold'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === 'simulation' && (
          <div className="space-y-4">
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
                <label className="text-xs text-gray-400">开始时间</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={startHour}
                  onChange={(e) => setStartHour(parseInt(e.target.value))}
                  className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-400">结束时间</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={endHour}
                  onChange={(e) => setEndHour(parseInt(e.target.value))}
                  className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-300">天空模型</label>
              <select
                value={skyModel}
                onChange={(e) => setSkyModel(e.target.value as any)}
                className="w-full bg-black/30 border border-white/20 rounded px-3 py-2 text-sm"
              >
                <option value="perez">Perez 模型（真实天空）</option>
                <option value="cie_clear">CIE 晴天模型</option>
                <option value="cie_overcast">CIE 阴天模型</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-300">网格分辨率: {gridResolution}</label>
              <input
                type="range"
                min="5"
                max="20"
                value={gridResolution}
                onChange={(e) => setGridResolution(parseInt(e.target.value))}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-300">大气浑浊度: {turbidity.toFixed(1)}</label>
              <input
                type="range"
                min="1"
                max="10"
                step="0.5"
                value={turbidity}
                onChange={(e) => setTurbidity(parseFloat(e.target.value))}
                className="w-full"
              />
            </div>

            <button
              onClick={runSimulation}
              disabled={simulationStatus === 'running'}
              className="w-full py-2.5 bg-gradient-to-r from-ancient-wood to-ancient-gold text-white rounded font-medium text-sm hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {simulationStatus === 'running' ? '仿真进行中...' : '运行采光仿真'}
            </button>

            {simulationStatus === 'running' && (
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-gray-400">
                  <span>进度</span>
                  <span>{Math.round(simulationProgress)}%</span>
                </div>
                <div className="w-full h-2 bg-black/30 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-ancient-gold to-yellow-400 transition-all duration-300"
                    style={{ width: `${simulationProgress}%` }}
                  />
                </div>
              </div>
            )}

            {simulationStatus === 'completed' && simulationResult && (
              <div className="p-3 bg-ancient-wood/20 rounded border border-ancient-gold/30">
                <div className="text-xs text-ancient-gold font-semibold mb-2">仿真完成</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-400">平均照度:</span>{' '}
                    {formatIlluminance(simulationResult.avg_illuminance)}
                  </div>
                  <div>
                    <span className="text-gray-400">均匀度:</span>{' '}
                    {(simulationResult.uniformity * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-2 pt-2 border-t border-white/10">
              <label className="text-sm text-gray-300">时间滑块: {selectedHour.toString().padStart(2, '0')}:00</label>
              <input
                type="range"
                min={startHour}
                max={endHour}
                value={selectedHour}
                onChange={(e) => handleHourChange(parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>{startHour.toString().padStart(2, '0')}:00</span>
                <span>{endHour.toString().padStart(2, '0')}:00</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'optimization' && (
          <div className="space-y-4">
            <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded text-xs text-blue-200">
              <div className="font-semibold mb-1">💡 粒子群优化算法</div>
              <p>基于窗户位置和尺寸参数，优化室内采光均匀度。</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-gray-400">窗户数量</label>
                <input
                  type="number"
                  min="1"
                  max="8"
                  value={optimizationParams.num_windows}
                  onChange={(e) => setOptimizationParams({...optimizationParams, num_windows: parseInt(e.target.value)})}
                  className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-400">种群大小</label>
                <input
                  type="number"
                  min="10"
                  max="100"
                  value={optimizationParams.population_size}
                  onChange={(e) => setOptimizationParams({...optimizationParams, population_size: parseInt(e.target.value)})}
                  className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-gray-400">最大迭代</label>
                <input
                  type="number"
                  min="10"
                  max="200"
                  value={optimizationParams.max_iterations}
                  onChange={(e) => setOptimizationParams({...optimizationParams, max_iterations: parseInt(e.target.value)})}
                  className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-400">目标均匀度</label>
                <input
                  type="number"
                  min="0.5"
                  max="0.95"
                  step="0.05"
                  value={optimizationParams.target_uniformity}
                  onChange={(e) => setOptimizationParams({...optimizationParams, target_uniformity: parseFloat(e.target.value)})}
                  className="w-full bg-black/30 border border-white/20 rounded px-2 py-1.5 text-sm"
                />
              </div>
            </div>

            <button
              onClick={runOptimization}
              disabled={optimizationStatus === 'running'}
              className="w-full py-2.5 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded font-medium text-sm hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {optimizationStatus === 'running' ? '优化进行中...' : '运行日照优化'}
            </button>

            {optimizationStatus === 'running' && (
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-gray-400">
                  <span>优化进度</span>
                  <span>{Math.round(optimizationProgress)}%</span>
                </div>
                <div className="w-full h-2 bg-black/30 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-300"
                    style={{ width: `${optimizationProgress}%` }}
                  />
                </div>
              </div>
            )}

            {optimizationResult && (
              <div className="p-3 bg-purple-500/10 rounded border border-purple-500/30 space-y-2">
                <div className="text-xs text-purple-300 font-semibold">✨ 优化完成</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-400">最佳适应度:</span>{' '}
                    {optimizationResult.best_fitness.toFixed(3)}
                  </div>
                  <div>
                    <span className="text-gray-400">均匀度:</span>{' '}
                    {(optimizationResult.uniformity * 100).toFixed(1)}%
                  </div>
                  <div>
                    <span className="text-gray-400">迭代次数:</span>{' '}
                    {optimizationResult.iterations}
                  </div>
                  <div>
                    <span className="text-gray-400">平均照度:</span>{' '}
                    {formatIlluminance(optimizationResult.avg_illuminance)}
                  </div>
                </div>
                <div className="text-xs text-gray-400">
                  最优窗户方案已应用到3D模型
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'alert' && (
          <div className="space-y-4">
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded text-xs">
              <div className="font-semibold text-red-300 mb-1">⚠️ 冬季日照告警</div>
              <p className="text-gray-300">当日照时长低于3小时时，将触发告警并通过MQTT推送。</p>
            </div>

            <button
              onClick={async () => {
                try {
                  await alertAPI.check();
                } catch (e) {
                  console.error(e);
                }
              }}
              className="w-full py-2 bg-red-600/80 text-white rounded text-sm hover:bg-red-600 transition"
            >
              检查日照时长
            </button>

            <button
              onClick={async () => {
                try {
                  await alertAPI.sendTest();
                } catch (e) {
                  console.error(e);
                }
              }}
              className="w-full py-2 bg-gray-600/80 text-white rounded text-sm hover:bg-gray-600 transition"
            >
              发送测试告警
            </button>

            <div className="pt-2 border-t border-white/10">
              <div className="text-xs text-gray-400 mb-2">告警说明</div>
              <div className="space-y-1 text-xs text-gray-300">
                <div>• 检查时段: 冬季（11月-次年2月）</div>
                <div>• 阈值: 日照时长 &lt; 3小时/天</div>
                <div>• 推送方式: MQTT消息</div>
                <div>• 主题: mingtang/alerts</div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'display' && (
          <div className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">显示伪彩色云图</span>
                <button
                  onClick={() => setShowCloudMap(!showCloudMap)}
                  className={`w-12 h-6 rounded-full transition-colors ${
                    showCloudMap ? 'bg-ancient-gold' : 'bg-gray-600'
                  }`}
                >
                  <div
                    className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                      showCloudMap ? 'translate-x-6' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>

              <div className="space-y-2">
                <label className="text-sm text-gray-300">
                  云图透明度: {(cloudMapOpacity * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="1"
                  step="0.05"
                  value={cloudMapOpacity}
                  onChange={(e) => setCloudMapOpacity(parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">自动旋转视角</span>
                <button
                  onClick={() => setAutoRotate(!autoRotate)}
                  className={`w-12 h-6 rounded-full transition-colors ${
                    autoRotate ? 'bg-ancient-gold' : 'bg-gray-600'
                  }`}
                >
                  <div
                    className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                      autoRotate ? 'translate-x-6' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">线框模式</span>
                <button
                  onClick={() => setWireframeMode(!wireframeMode)}
                  className={`w-12 h-6 rounded-full transition-colors ${
                    wireframeMode ? 'bg-ancient-gold' : 'bg-gray-600'
                  }`}
                >
                  <div
                    className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                      wireframeMode ? 'translate-x-6' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>
            </div>

            <div className="pt-3 border-t border-white/10">
              <div className="text-xs text-gray-400 mb-2">图例说明</div>
              <div className="h-4 gradient-legend rounded" />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>低</span>
                <span>照度</span>
                <span>高</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ControlPanel;
