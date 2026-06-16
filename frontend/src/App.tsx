import React, { useState, useEffect } from 'react';
import { useAppStore } from '@/store';
import { alertAPI } from '@/api';
import { Mingtang3DModel } from './modules/mingtang_3d';
import { LightCloudMap, ControlPanel, SensorPanel, AlertNotification } from './modules/daylight_panel';

const App: React.FC = () => {
  const { simulationResult, latestSensorData, optimizedWindows, selectedHour, selectedDate } = useAppStore();
  const [cloudMapSize, setCloudMapSize] = useState({ width: 600, height: 500 });
  const [activeView, setActiveView] = useState<'3d' | 'cloud'>('3d');
  const [connected, setConnected] = useState(true);

  useEffect(() => {
    const updateSize = () => {
      const container = document.getElementById('cloudmap-container');
      if (container) {
        setCloudMapSize({
          width: container.clientWidth,
          height: container.clientHeight
        });
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  useEffect(() => {
    let mqttClient: any = null;

    const setupMQTT = async () => {
      try {
        const mqtt = await import('mqtt');

        const client = mqtt.connect('ws://localhost:9001/mqtt', {
          clientId: `frontend_${Math.random().toString(16).substr(2, 8)}`,
          reconnectPeriod: 5000,
        });

        client.on('connect', () => {
          console.log('MQTT connected');
          setConnected(true);
          client.subscribe('mingtang/alerts');
        });

        client.on('message', (topic: string, message: Buffer) => {
          if (topic === 'mingtang/alerts') {
            try {
              const alert = JSON.parse(message.toString());
              console.log('Received alert:', alert);
              alert('【告警】' + alert.message);
            } catch (e) {
              console.error('Failed to parse alert:', e);
            }
          }
        });

        client.on('error', (err: Error) => {
          console.error('MQTT error:', err);
          setConnected(false);
        });

        client.on('close', () => {
          setConnected(false);
        });

        mqttClient = client;
      } catch (e) {
        console.warn('MQTT not available, continuing without real-time alerts');
      }
    };

    setupMQTT();

    return () => {
      if (mqttClient) {
        mqttClient.end();
      }
    };
  }, []);

  const solarAltitude = latestSensorData.length > 0
    ? latestSensorData[0].solar_altitude
    : 45;
  const solarAzimuth = latestSensorData.length > 0
    ? latestSensorData[0].solar_azimuth
    : 180;

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const months = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二'];
    return `${months[date.getMonth()]}月${date.getDate()}日`;
  };

  return (
    <div className="w-full h-screen flex flex-col bg-[#0a0a1a] overflow-hidden">
      <header className="h-16 border-b border-white/10 flex items-center justify-between px-6 bg-gradient-to-r from-black/50 to-transparent">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-ancient-wood to-ancient-gold flex items-center justify-center">
            <span className="text-xl">🏛️</span>
          </div>
          <div>
            <h1 className="ancient-title text-xl">古代明堂建筑采光仿真与日照优化系统</h1>
            <p className="text-xs text-gray-500">汉长安明堂遗址数字化复原研究平台</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/30">
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-sensor-good animate-pulse' : 'bg-sensor-danger'}`} />
            <span className="text-xs text-gray-400">
              {connected ? 'MQTT已连接' : 'MQTT未连接'}
            </span>
          </div>

          <div className="text-right">
            <div className="text-sm text-gray-300">{formatDate(selectedDate)}</div>
            <div className="text-xs text-ancient-gold">{selectedHour.toString().padStart(2, '0')}:00</div>
          </div>

          <div className="relative">
            <AlertNotification />
          </div>

          <div className="flex items-center gap-1 border border-white/10 rounded-lg overflow-hidden">
            <button
              onClick={() => setActiveView('3d')}
              className={`px-3 py-1.5 text-xs transition ${
                activeView === '3d'
                  ? 'bg-ancient-gold text-black font-medium'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              3D视图
            </button>
            <button
              onClick={() => setActiveView('cloud')}
              className={`px-3 py-1.5 text-xs transition ${
                activeView === 'cloud'
                  ? 'bg-ancient-gold text-black font-medium'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              采光云图
            </button>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside className="w-80 border-r border-white/10 flex flex-col">
          <SensorPanel />
        </aside>

        <main className="flex-1 relative">
          {activeView === '3d' ? (
            <div className="w-full h-full">
              <Mingtang3DModel
                solarAltitude={solarAltitude}
                solarAzimuth={solarAzimuth}
                windows={optimizedWindows}
              />
            </div>
          ) : (
            <div id="cloudmap-container" className="w-full h-full p-4">
              <LightCloudMap
                simulationResult={simulationResult}
                width={cloudMapSize.width}
                height={cloudMapSize.height}
              />
            </div>
          )}

          <div className="absolute top-4 left-4 flex gap-2">
            <div className="glass-panel px-3 py-2 text-xs">
              <div className="text-gray-400 mb-1">太阳位置</div>
              <div className="flex gap-4">
                <span>高度: <span className="text-ancient-gold">{solarAltitude.toFixed(1)}°</span></span>
                <span>方位: <span className="text-ancient-gold">{solarAzimuth.toFixed(1)}°</span></span>
              </div>
            </div>

            {simulationResult && (
              <div className="glass-panel px-3 py-2 text-xs">
                <div className="text-gray-400 mb-1">采光指标</div>
                <div className="flex gap-4">
                  <span>平均: <span className="text-sensor-good">{(simulationResult.avg_illuminance).toFixed(0)} lux</span></span>
                  <span>均匀度: <span className={`${
                    simulationResult.uniformity > 0.7 ? 'text-sensor-good' :
                    simulationResult.uniformity > 0.5 ? 'text-sensor-warning' : 'text-sensor-danger'
                  }`}>
                    {(simulationResult.uniformity * 100).toFixed(1)}%
                  </span></span>
                </div>
              </div>
            )}
          </div>

          <div className="absolute bottom-4 left-4 glass-panel px-3 py-2 text-xs">
            <div className="text-gray-400 mb-1">操作提示</div>
            <div className="text-gray-500 space-y-0.5">
              <div>🖱️ 左键拖动: 旋转视角</div>
              <div>🖱️ 右键拖动: 平移</div>
              <div>🖱️ 滚轮: 缩放</div>
            </div>
          </div>
        </main>

        <aside className="w-96 border-l border-white/10 flex flex-col">
          <ControlPanel />
        </aside>
      </div>

      <footer className="h-8 border-t border-white/10 flex items-center justify-between px-6 text-xs text-gray-500">
        <div>
          汉长安明堂 · 建于西汉元始四年（公元4年）· 遗址坐标: 34.265°N, 108.954°E
        </div>
        <div className="flex items-center gap-4">
          <span>建筑史研究团队 © 2024</span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-sensor-good animate-pulse" />
            系统运行中
          </span>
        </div>
      </footer>
    </div>
  );
};

export default App;
