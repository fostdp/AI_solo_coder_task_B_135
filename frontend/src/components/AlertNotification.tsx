import React, { useEffect, useState } from 'react';
import { useAppStore } from '@/store';
import { alertAPI } from '@/api';
import type { AlertRecord } from '@/types';

const AlertNotification: React.FC = () => {
  const { alerts, setAlerts, addAlert } = useAppStore();
  const [showAlertPanel, setShowAlertPanel] = useState(false);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await alertAPI.getHistory({ limit: 20 });
        setAlerts(response.data as AlertRecord[]);
      } catch (e) {
        console.error('Failed to fetch alerts:', e);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);

    return () => clearInterval(interval);
  }, [setAlerts]);

  const unreadCount = alerts.filter(a => !a.acknowledged).length;

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getAlertTypeLabel = (type: string) => {
    switch (type) {
      case 'winter_sunshine': return '冬季日照不足';
      case 'test': return '测试告警';
      default: return type;
    }
  };

  return (
    <>
      <button
        onClick={() => setShowAlertPanel(!showAlertPanel)}
        className="relative p-2 rounded-lg hover:bg-white/10 transition"
      >
        <svg className="w-6 h-6 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className={`absolute -top-1 -right-1 w-5 h-5 rounded-full text-xs flex items-center justify-center ${
            unreadCount > 5 ? 'bg-sensor-danger alert-pulse' : 'bg-ancient-gold'
          } text-white`}>
            {unreadCount}
          </span>
        )}
      </button>

      {showAlertPanel && (
        <div className="absolute right-0 top-full mt-2 w-96 max-h-[500px] glass-panel overflow-hidden z-50">
          <div className="p-3 border-b border-white/10 flex items-center justify-between">
            <h3 className="font-semibold text-ancient-gold">告警消息</h3>
            <button
              onClick={() => setShowAlertPanel(false)}
              className="text-gray-400 hover:text-white text-xl leading-none"
            >
              ×
            </button>
          </div>

          <div className="overflow-y-auto max-h-[400px]">
            {alerts.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <div className="text-3xl mb-2">✅</div>
                <p className="text-sm">暂无告警消息</p>
              </div>
            ) : (
              <div className="divide-y divide-white/10">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-3 ${!alert.acknowledged ? 'bg-sensor-danger/10' : ''}`}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        alert.alert_type === 'test'
                          ? 'bg-gray-600 text-gray-200'
                          : 'bg-sensor-danger/30 text-sensor-danger'
                      }`}>
                        {getAlertTypeLabel(alert.alert_type)}
                      </span>
                      {!alert.acknowledged && (
                        <span className="w-2 h-2 rounded-full bg-sensor-danger animate-pulse" />
                      )}
                    </div>
                    <p className="text-sm text-gray-300 mb-1">{alert.message}</p>
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>{formatTime(alert.timestamp)}</span>
                      <span>日照时长: {alert.sunshine_hours.toFixed(1)}h / 阈值: {alert.threshold}h</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default AlertNotification;
