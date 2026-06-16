# 汉长安明堂遗址数字化复原 - 采光仿真与日照优化系统

## 项目简介

本系统是为汉长安明堂遗址数字化复原研究而开发的全栈应用，集成了采光仿真、日照优化、传感器数据采集和MQTT告警推送功能。

**研究背景**：汉长安明堂建于西汉元始四年（公元4年），是古代帝王宣明政教、举行大典的重要场所。本系统通过计算机仿真技术，复原研究古代明堂建筑的采光性能，为建筑史研究提供量化数据支持。

---

## 系统架构

### 整体架构图

```
                           ┌─────────────────────────────────────────────────────────────┐
                           │                     前端 (React + Three.js)          │
                           │  ┌──────────────┐    ┌──────────────────┐      │
                           │  │  明堂3D模型  │    │  采光云图/控制面板 │      │
                           │  └──────────────┘    └──────────────────┘      │
                           └───────────────────────────┬─────────────────────────────────┘
                                                       │ :80/3000
                                                       │ Nginx (Gzip压缩)
                                                       ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                                  微服务层 (FastAPI + Gunicorn + Uvicorn Workers)  │
│                                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ dtu_receiver│  │daylight_sim │  │sunlight_opt  │  │ alarm_mqtt   │    │
│  │   :8001     │  │   :8002     │  │   :8003     │  │   :8004     │    │
│  │ 传感器采集  │  │ 光线追踪仿真 │  │ PSO优化器    │  │ MQTT告警推送│    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼───────────────────┼───────────────────┼───────────────────┼────────────┘
          │                   │                   │                   │
          └───────────────────┬───┴───────────────────┴───────────────────┘
                          │        Redis Pub/Sub (消息总线)
                          ▼
                ┌──────────────────────┐
                │   Redis :6379     │
                └─────────┬────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│  InfluxDB   │  │   Mosquitto │  │Sensor Simulator│
│   :8086     │  │ MQTT :1883 │  │ (季节/窗户配置)│
│ 3级降采样   │  │ WS :9001    │  └──────────────────┘
└──────────────┘  └──────────────┘
```

### 微服务端口映射

| 服务 | 端口 | 说明 |
|------|------|------|
| dtu_receiver | 8001 | 传感器数据接收、查询、统计 |
| daylight_simulator | 8002 | 光线追踪照度仿真 |
| sunlight_optimizer | 8003 | PSO粒子群窗户优化 |
| alarm_mqtt | 8004 | 日照告警评估+MQTT推送 |
| influxdb | 8086 | 时序数据库 |
| redis | 6379 | Pub/Sub消息总线 |
| mosquitto | 1883/9001 | MQTT Broker (TCP/WebSocket) |
| frontend | 3000 | Nginx前端+反向代理 |

### InfluxDB数据分层（3级降采样）

```
mingtang_data (原始)  ──1小时──▶  mingtang_data_hourly  ──1天──▶  mingtang_data_daily
    30天 RP             180天 RP               永久保留 RP
  传感器原始数据        小时级均值聚合           日级均值聚合
```

---

## 目录结构

```
AI_solo_coder_task_A_135/
├── backend/                          # 后端微服务
│   ├── dtu_receiver/              # 传感器数据接收微服务 (:8001)
│   ├── daylight_simulator/         # 日光仿真微服务 (:8002)
│   ├── sunlight_optimizer/      # 日照优化微服务 (:8003)
│   ├── alarm_mqtt/               # MQTT告警微服务 (:8004)
│   ├── shared/                    # 共享模块(config/database/redis/schemas)
│   ├── config/                    # JSON外置配置(4个文件)
│   │   ├── optical_params.json
│   │   ├── sky_model_params.json
│   │   ├── optimizer_params.json
│   │   └── alarm_params.json
│   ├── scripts/                   # 工具脚本
│   │   ├── init_influxdb.py       # DB初始化+降采样Task创建
│   │   ├── sensor_simulator.py   # 传感器模拟器(支持季节/窗户配置)
│   │   └── regression_test.py  # 回归测试
│   ├── docker/                    # Dockerfile
│   │   ├── Dockerfile.dtu_receiver
│   │   ├── Dockerfile.daylight_simulator
│   │   ├── Dockerfile.sunlight_optimizer
│   │   ├── Dockerfile.alarm_mqtt
│   │   └── Dockerfile.sensor_simulator
│   └── requirements.txt
├── frontend/                       # 前端(React + Three.js)
│   ├── src/
│   │   ├── modules/
│   │   │   ├── mingtang_3d/      # 3D模型模块
│   │   │   └── daylight_panel/ # 控制面板+云图+传感器面板
│   ├── nginx.conf                # Nginx配置(Gzip+反向代理
│   ├── vite.config.ts            # Vite配置(Gzip压缩+代码分割)
│   └── Dockerfile
├── mosquitto/                      # MQTT Broker配置
│   └── mosquitto.conf
├── docker-compose.yml            # Docker Compose编排
└── README.md
```

---

## 核心功能

### 1. 采光仿真模型
- **天空模型**：Perez真实天空、CIE晴天、CIE阴天三种模型
- **光线追踪**：直接光照 + 漫反射 + 3次弹射路径追踪
- **空间离散**：三维网格照度分布矩阵
- **时间序列**：逐小时仿真 + 全日照变化曲线

### 2. 日照优化引擎
- **PSO粒子群**：多目标优化(均匀度/平均照度/窗户效率
- **NSGA-II**：快速非支配排序 + Pareto最优
- **约束条件**：窗户不重叠、墙面边界
- **输出**：最优窗户方案、收敛曲线、优化前后对比

### 3. 传感器数据采集
- **6监测点**：主殿、东/西/南/北室、中心祭台
- **参数**：照度、太阳高度角、方位角、温度、季节标签
- **存储**：InfluxDB三级降采样

### 4. 告警系统
- **触发条件**：冬季日照不足预警
- **推送**：MQTT (主题: `mingtang/alerts`)
- **等级**：轻度(2-3h)、中度(1-2h)、严重(<1h)

---

## 技术栈

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11 | 开发语言 |
| FastAPI | 0.104.x | Web框架 |
| Gunicorn | 21.x | WSGI服务器 |
| Uvicorn | 0.24.x | ASGI Worker |
| InfluxDB | 2.7 | 时序数据库 |
| Redis | 7 | Pub/Sub |
| Mosquitto | 2.0 | MQTT Broker |
| NumPy/SciPy | 最新 | 科学计算 |
| Docker | - | 容器化 |

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.2 | UI框架 |
| TypeScript | 5.3 | 类型系统 |
| Vite | 5.0 | 构建工具(Gzip/Brotli压缩) |
| Three.js | 0.160 | 三维渲染 |
| Nginx | 1.25 | 反向代理+Gzip静态压缩 |
| ECharts | 5.4 | 数据可视化 |

---

## Docker Compose 部署步骤

### 前置条件

- Docker 20.10+
- Docker Compose v2+

### 一键启动

```bash
# 1. 克隆项目并进入目录
cd AI_solo_coder_task_A_135

# 2. 启动核心服务（InfluxDB+Redis+Mosquitto+4微服务+前端）
docker-compose up -d

# 3. 查看服务启动状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f dtu_receiver
```

### 启动传感器模拟器

模拟器服务放在独立profile，按需启动：

```bash
# 启动默认配置的模拟器（自动季节模式
docker-compose --profile simulator up -d sensor_simulator

# 指定季节启动（如冬季）
SIMULATOR_SEASON=winter docker-compose --profile simulator up -d sensor_simulator

# 回填7天夏季数据
docker-compose run --rm sensor_simulator \
  python /app/sensor_simulator.py \
  --mode backfill \
  --season summer \
  --backfill-days 7 \
  --api-url http://dtu_receiver:8001
```

### 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并清除数据卷
docker-compose down -v
```

### 服务访问地址

启动成功后访问：

| 服务 | 地址 |
|------|------|
| 前端主页 | http://localhost:3000 |
| DTU API文档 | http://localhost:8001/docs |
| 仿真API文档 | http://localhost:8002/docs |
| 优化API文档 | http://localhost:8003/docs |
| 告警API文档 | http://localhost:8004/docs |
| InfluxDB UI | http://localhost:8086 |
| MQTT WebSocket | ws://localhost:9001/mqtt |

---

## 传感器模拟器用法

模拟器支持**季节配置**和**自定义窗户配置**。

### 基本参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | 运行模式 | `continuous` 或 `backfill` |
| `--season` | 季节配置 | spring/summer/autumn/winter，不指定自动判断 |
| `--api-url` | DTU服务地址 | http://localhost:8001 |
| `--interval` | 上报间隔(秒) | 3600 |
| `--backfill-days` | 回填天数 | 7 |
| `--window-config` | 窗户配置JSON路径 | - |
| `--generate-window-config` | 生成示例窗户配置 | - |

### 季节配置说明

模拟器内置四季气象参数：

| 季节 | 太阳偏角 | 云量范围 | 天气因子 | DNI倍率 | 温度范围 |
|--------|----------|-----------|----------|----------|
| spring | +0° | 0.2-0.6 | 0.7-1.0 | ×0.9 | 10-25°C |
| summer | +5° | 0.3-0.8 | 0.6-1.0 | ×1.15 | 25-38°C |
| autumn | -2° | 0.2-0.5 | 0.75-1.0 | ×0.85 | 8-22°C |
| winter | -8° | 0.4-0.85 | 0.4-0.8 | ×0.6 | -5-10°C |

### 用法示例

#### 1. 连续模式 - 不同季节

```bash
cd backend

# 春季（自动判断
python scripts/sensor_simulator.py --mode continuous

# 强制冬季模式（模拟低照度场景
python scripts/sensor_simulator.py --season winter --interval 1800

# 夏季模式 + 30分钟间隔
python scripts/sensor_simulator.py --season summer --interval 1800
```

#### 2. 回填模式 - 历史数据

```bash
# 回填7天冬季数据（测试告警触发
python scripts/sensor_simulator.py --mode backfill --season winter --backfill-days 7

# 回填30天全年四季数据（不指定季节自动判断
python scripts/sensor_simulator.py --mode backfill --backfill-days 30
```

#### 3. 自定义窗户配置

```bash
# 先生成示例配置文件模板
python scripts/sensor_simulator.py --generate-window-config ./my_windows.json

# 编辑 my_windows.json 后，使用自定义配置运行
python scripts/sensor_simulator.py --season spring --window-config ./my_windows.json
```

#### 4. Docker中运行

```bash
# Docker内执行
docker-compose run --rm sensor_simulator \
  python /app/sensor_simulator.py \
  --season winter \
  --window-config /app/config/windows.json
```

### 窗户配置文件格式

```json
{
  "description": "明堂窗户配置
  "building": "han_changan_mingtang",
  "windows": [
    {
      "window_id": "window_south_main",
      "face": "south",
      "position_x": 0.0,
      "position_y": 1.2,
      "width": 3.0,
      "height": 2.2,
      "transmittance": 0.70,
      "description": "南墙主窗"
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| window_id | 窗户唯一ID |
| face | 朝向: south/east/west/north |
| position_x/y | 窗户位置(m) |
| width/height | 窗户尺寸(m) |
| transmittance | 透光率 0-1 |

---

## 核心算法

### Perez天空模型

```
L(θ, γ) = Lz * [1 + a*exp(b/cosθ)] * [1 + c*exp(d*γ) + e*cos²γ]
```

### PSO粒子群

```
v_i(t+1) = w*v_i(t) + c1*r1*(pbest_i - x_i(t)) + c2*r2*(gbest - x_i(t))
x_i(t+1) = x_i(t) + v_i(t+1)
```

### 多目标适应度

```
fitness = α*uniformity + β*(avg_illuminance/target + γ*window_efficiency
```

---

## 常见问题

### Q: InfluxDB初始化失败？

检查docker-compose logs influxdb容器健康状态，首次初始化需要约30秒。

### Q: MQTT连接不上？

确认mosquitto.conf中`listener 9001 protocol websockets是否开启，前端通过9001端口WebSocket连接。

### Q: 仿真太慢？

降低grid分辨率，减少反射次数。

### Q: 模拟器如何测试告警？

```bash
# 回填7天冬季数据后调用告警检查API：
curl -X POST http://localhost:8004/api/alert/check
```

---

## 研究用途

仅用于学术研究。
