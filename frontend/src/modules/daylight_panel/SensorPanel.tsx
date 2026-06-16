import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { useAppStore } from '@/store';
import { sensorAPI } from '@/api';
import { jetColorMapCSS, formatIlluminance } from './colorMap';
import { SENSOR_LOCATIONS } from '../mingtang_3d';
import type { SensorData } from '@/types';

const SensorPanel: React.FC = () => {
  const { latestSensorData, setLatestSensorData, selectedDate, selectedHour } = useAppStore();
  const [activeSensor, setActiveSensor] = useState<string>('main_hall');
  const [historyData, setHistoryData] = useState<SensorData[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [latest, history] = await Promise.all([
          sensorAPI.getLatest(),
          sensorAPI.getData({
            start_time: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
            limit: 100
          })
        ]);
        setLatestSensorData(latest.data);
        setHistoryData(history.data);
      } catch (error) {
        console.error('Failed to fetch sensor data:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000);

    return () => clearInterval(interval);
  }, [setLatestSensorData]);

  const getSensorData = (location: string) => {
    return latestSensorData.find(d => d.location === location);
  };

  const getLocationLabel = (name: string) => {
    return SENSOR_LOCATIONS.find(s => s.name === name)?.label || name;
  };

  const chartOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(30, 30, 50, 0.9)',
      borderColor: 'rgba(212, 175, 55, 0.5)',
      textStyle: { color: '#e8e8e8' },
      formatter: (params: any) => {
        const data = params[0];
        return `${data.axisValue}<br/>照度: ${formatIlluminance(data.value)}`;
      }
    },
    grid: {
      left: '10%',
      right: '5%',
      top: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: historyData
        .filter(d => d.location === activeSensor)
        .map(d => new Date(d.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })),
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.2)' } },
      axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: 'lux',
      nameTextStyle: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.2)' } },
      axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }
    },
    series: [{
      data: historyData
        .filter(d => d.location === activeSensor)
        .map(d => d.illuminance),
      type: 'line',
      smooth: true,
      lineStyle: {
        color: '#D4AF37',
        width: 2
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(212, 175, 55, 0.3)' },
            { offset: 1, color: 'rgba(212, 175, 55, 0)' }
          ]
        }
      },
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: { color: '#D4AF37' }
    }]
  };

  return (
    <div className="h-full flex flex-col glass-panel overflow-hidden">
      <div className="p-4 border-b border-white/10">
        <h2 className="ancient-title text-lg">传感器数据</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="grid grid-cols-3 gap-2">
          {SENSOR_LOCATIONS.map(sensor => {
            const data = getSensorData(sensor.name);
            const isActive = activeSensor === sensor.name;

            return (
              <button
                key={sensor.name}
                onClick={() => setActiveSensor(sensor.name)}
                className={`p-3 rounded text-left transition ${
                  isActive
                    ? 'bg-ancient-wood/40 border border-ancient-gold/50'
                    : 'bg-black/30 border border-transparent hover:border-white/20'
                }`}
              >
                <div className="text-xs text-gray-400 mb-1">{sensor.label}</div>
                {data ? (
                  <div className="space-y-1">
                    <div
                      className="font-mono text-sm font-semibold"
                      style={{ color: jetColorMapCSS(data.illuminance, 0, 2000).replace('0.7', '1') }}
                    >
                      {formatIlluminance(data.illuminance)}
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 rounded-full bg-sensor-good animate-pulse" />
                      <span className="text-[10px] text-gray-500">
                        太阳高度: {data.solar_altitude.toFixed(1)}°
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-gray-600">无数据</div>
                )}
              </button>
            );
          })}
        </div>

        <div className="glass-panel p-3">
          <div className="text-sm text-gray-300 mb-2">
            {getLocationLabel(activeSensor)} - 24小时照度变化
          </div>
          <div className="h-48">
            <ReactECharts
              option={chartOption}
              style={{ height: '100%', width: '100%' }}
              notMerge={true}
              lazyUpdate={true}
            />
          </div>
        </div>

        {latestSensorData.length > 0 && (
          <div className="glass-panel p-3 space-y-2">
            <div className="text-sm text-gray-300 mb-2">当前时间: {selectedDate} {selectedHour.toString().padStart(2, '0')}:00</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-400">太阳高度:</span>{' '}
                {latestSensorData[0]?.solar_altitude.toFixed(1)}°
              </div>
              <div>
                <span className="text-gray-400">太阳方位:</span>{' '}
                {latestSensorData[0]?.solar_azimuth.toFixed(1)}°
              </div>
              <div>
                <span className="text-gray-400">窗户透光率:</span>{' '}
                {(latestSensorData[0]?.window_transmittance * 100).toFixed(0)}%
              </div>
              <div>
                <span className="text-gray-400">传感器数量:</span>{' '}
                {latestSensorData.length}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SensorPanel;
