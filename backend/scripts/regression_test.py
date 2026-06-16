#!/usr/bin/env python3
"""
明堂采光仿真系统 — 微服务拆分功能回归测试
测试四个微服务的核心API端点和Redis Pub/Sub通信
"""
import sys
import os
import json
import time
import uuid
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.warning("redis package not installed, skipping Redis tests")

PASS_COUNT = 0
FAIL_COUNT = 0
SKIP_COUNT = 0


def record_result(name: str, passed: bool, detail: str = ""):
    global PASS_COUNT, FAIL_COUNT
    if passed:
        PASS_COUNT += 1
        logger.info(f"  ✅ PASS: {name}")
    else:
        FAIL_COUNT += 1
        logger.error(f"  ❌ FAIL: {name} — {detail}")


def record_skip(name: str, reason: str = ""):
    global SKIP_COUNT
    SKIP_COUNT += 1
    logger.warning(f"  ⏭️  SKIP: {name} — {reason}")


class RegressionTestSuite:
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        self.shared_dir = os.path.join(os.path.dirname(__file__), '..', 'shared')

    def test_json_config_files(self):
        """测试JSON配置文件可加载且结构正确"""
        logger.info("=== 1. JSON配置文件测试 ===")

        config_files = {
            'sky_model_params.json': ['perez', 'cie_clear', 'cie_overcast', 'defaults'],
            'optical_params.json': ['materials', 'ray_tracer', 'building', 'grid'],
            'optimizer_params.json': ['pso', 'bounds', 'multi_objective', 'fitness', 'defaults'],
            'alarm_params.json': ['alert', 'mqtt', 'recommendations'],
        }

        for filename, required_keys in config_files.items():
            filepath = os.path.join(self.config_dir, filename)
            try:
                assert os.path.exists(filepath), f"File not found: {filepath}"
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                assert isinstance(data, dict), f"Not a dict: {type(data)}"
                for key in required_keys:
                    assert key in data, f"Missing key: {key}"
                record_result(f"JSON配置: {filename}", True)
            except Exception as e:
                record_result(f"JSON配置: {filename}", False, str(e))

    def test_sky_model_params(self):
        """测试天空模型参数的具体数值合理性"""
        logger.info("=== 2. 天空模型参数合理性测试 ===")

        filepath = os.path.join(self.config_dir, 'sky_model_params.json')
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        try:
            perez = data['perez']
            assert len(perez['coefficients_luminance']) == 5, "Perez应有5组系数"
            for coeff in perez['coefficients_luminance']:
                assert len(coeff) == 2, "每组系数应有2个值"
            record_result("Perez系数维度", True)
        except Exception as e:
            record_result("Perez系数维度", False, str(e))

        try:
            overcast = data['cie_overcast']
            zenith = overcast['zenith_luminance']
            assert zenith['cloud_base'] > 0, "cloud_base应>0"
            assert zenith['cloud_altitude_factor'] > 0, "cloud_altitude_factor应>0"
            assert 0 <= zenith['cloud_cover_weight'] <= 1, "cloud_cover_weight应在[0,1]"
            record_result("CIE阴天天顶亮度参数", True)
        except Exception as e:
            record_result("CIE阴天天顶亮度参数", False, str(e))

        try:
            defaults = data['defaults']
            assert 1.0 <= defaults['turbidity'] <= 10.0, "turbidity应在[1,10]"
            assert 0 <= defaults['ground_albedo'] <= 1.0, "ground_albedo应在[0,1]"
            assert defaults['solar_constant'] > 1000, "solar_constant应>1000"
            record_result("默认参数合理性", True)
        except Exception as e:
            record_result("默认参数合理性", False, str(e))

    def test_optical_params(self):
        """测试光学参数的完整性和合理性"""
        logger.info("=== 3. 光学参数完整性测试 ===")

        filepath = os.path.join(self.config_dir, 'optical_params.json')
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        required_materials = ['floor', 'wall', 'roof', 'column', 'window', 'ground']
        for mat_name in required_materials:
            try:
                mat = data['materials'][mat_name]
                assert 'albedo' in mat, f"{mat_name}缺少albedo"
                assert 'reflectivity' in mat, f"{mat_name}缺少reflectivity"
                assert 'transmittance' in mat, f"{mat_name}缺少transmittance"
                assert 0 <= mat['reflectivity'] <= 1, f"{mat_name}反射率应在[0,1]"
                assert 0 <= mat['transmittance'] <= 1, f"{mat_name}透光率应在[0,1]"
                record_result(f"材质参数: {mat_name}", True)
            except Exception as e:
                record_result(f"材质参数: {mat_name}", False, str(e))

        try:
            rt = data['ray_tracer']
            assert rt['max_depth'] >= 1, "max_depth应>=1"
            assert rt['hemisphere_samples'] >= 1, "hemisphere_samples应>=1"
            assert 0 < rt['bias'] < 0.1, "bias应在(0, 0.1)"
            record_result("光线追踪参数", True)
        except Exception as e:
            record_result("光线追踪参数", False, str(e))

        try:
            bld = data['building']
            assert bld['length'] > 0 and bld['width'] > 0 and bld['height'] > 0
            assert len(bld['default_windows']) >= 4, "至少4扇默认窗户"
            for win in bld['default_windows']:
                assert 'position' in win and len(win['position']) == 3
                assert 'size' in win and len(win['size']) == 2
                assert 0 < win['transmittance'] <= 1
            record_result("建筑几何参数", True)
        except Exception as e:
            record_result("建筑几何参数", False, str(e))

    def test_optimizer_params(self):
        """测试优化器参数"""
        logger.info("=== 4. 优化器参数测试 ===")

        filepath = os.path.join(self.config_dir, 'optimizer_params.json')
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        try:
            pso = data['pso']
            assert 0 < pso['w_min'] < pso['w_max'] <= 1, "w_min < w_max应在(0,1]"
            assert pso['c1'] > 0 and pso['c2'] > 0, "c1,c2应>0"
            assert pso['local_search_freq'] > 0, "local_search_freq应>0"
            record_result("PSO参数合理性", True)
        except Exception as e:
            record_result("PSO参数合理性", False, str(e))

        try:
            bounds = data['bounds']
            for key in ['position_min', 'position_max', 'size_min', 'size_max']:
                assert key in bounds, f"缺少bounds.{key}"
            for i in range(3):
                assert bounds['position_min'][i] < bounds['position_max'][i], f"position_min[{i}] < position_max[{i}]"
            for i in range(2):
                assert bounds['size_min'][i] < bounds['size_max'][i], f"size_min[{i}] < size_max[{i}]"
            record_result("优化器边界参数", True)
        except Exception as e:
            record_result("优化器边界参数", False, str(e))

    def test_alarm_params(self):
        """测试告警参数"""
        logger.info("=== 5. 告警参数测试 ===")

        filepath = os.path.join(self.config_dir, 'alarm_params.json')
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        try:
            alert = data['alert']
            assert alert['min_daily_sunshine_hours'] > 0, "min_daily_sunshine_hours应>0"
            assert len(alert['alert_season']) > 0, "alert_season不能为空"
            assert 'season_months' in alert, "缺少season_months"
            for season, months in alert['season_months'].items():
                for m in months:
                    assert 1 <= m <= 12, f"{season}月份{m}不在1-12范围内"
            record_result("告警阈值参数", True)
        except Exception as e:
            record_result("告警阈值参数", False, str(e))

        try:
            mqtt = data['mqtt']
            assert mqtt['qos'] in [0, 1, 2], "QOS应为0/1/2"
            assert mqtt['keepalive'] > 0, "keepalive应>0"
            record_result("MQTT参数", True)
        except Exception as e:
            record_result("MQTT参数", False, str(e))

    def test_shared_schemas(self):
        """测试共享Schema模块可导入且结构正确"""
        logger.info("=== 6. 共享Schema模块测试 ===")

        try:
            from shared.schemas import (
                SensorDataPoint, SensorDataBatch, SensorDataQuery,
                SimulationParams, SimulationResultData, SimulationTaskResponse,
                OptimizationParams, OptimizationResultData, OptimizationTaskResponse,
                AlertConfig, AlertRecord, AlertType, SkyModelType,
                APIResponse, RedisChannels, TaskStatus,
            )
            record_result("Schema模块导入", True)
        except Exception as e:
            record_result("Schema模块导入", False, str(e))
            return

        try:
            sdp = SensorDataPoint(
                location="center",
                illuminance=500.0,
                solar_altitude=45.0,
                solar_azimuth=180.0,
                window_transmittance=0.7
            )
            assert sdp.illuminance == 500.0
            assert sdp.location == "center"
            record_result("SensorDataPoint构建", True)
        except Exception as e:
            record_result("SensorDataPoint构建", False, str(e))

        try:
            sp = SimulationParams(date="2024-12-21", start_hour=8, end_hour=16)
            assert sp.date == "2024-12-21"
            record_result("SimulationParams构建", True)
        except Exception as e:
            record_result("SimulationParams构建", False, str(e))

        try:
            assert RedisChannels.SENSOR_DATA == "sensor:data"
            assert RedisChannels.SIMULATION_RESULT == "simulation:result"
            assert RedisChannels.OPTIMIZATION_RESULT == "optimization:result"
            assert RedisChannels.ALERT_TRIGGERED == "alert:triggered"
            record_result("Redis频道常量", True)
        except Exception as e:
            record_result("Redis频道常量", False, str(e))

    def test_shared_config(self):
        """测试共享配置模块"""
        logger.info("=== 7. 共享配置模块测试 ===")

        try:
            from shared.config import shared_settings, load_json_config
            assert hasattr(shared_settings, 'redis_host')
            assert hasattr(shared_settings, 'influxdb_url')
            assert hasattr(shared_settings, 'mqtt_broker')
            assert hasattr(shared_settings, 'latitude')
            record_result("SharedSettings字段完整性", True)
        except Exception as e:
            record_result("SharedSettings字段完整性", False, str(e))

        try:
            from shared.config import load_json_config
            data = load_json_config("sky_model_params.json")
            assert 'perez' in data
            record_result("load_json_config加载", True)
        except Exception as e:
            record_result("load_json_config加载", False, str(e))

    def test_sky_model_with_config(self):
        """测试天空模型使用JSON配置"""
        logger.info("=== 8. 天空模型(配置驱动)测试 ===")

        try:
            from shared.config import load_json_config
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'daylight_simulator'))
            from simulation.sky_model import CIEOvercastSky, PerezSkyModel, SkyModelParameters

            config = load_json_config("sky_model_params.json")

            params = SkyModelParameters(
                solar_altitude=45.0,
                solar_azimuth=180.0,
                turbidity=2.5
            )

            overcast = CIEOvercastSky(params, cloud_cover=1.0, config=config.get('cie_overcast'))
            zenith_lum = overcast.get_sky_luminance(0, 0)
            assert zenith_lum > 100, f"阴天天顶亮度应>100 cd/m², 实际{zenith_lum:.1f}"
            diffuse = overcast.get_diffuse_irradiance()
            assert diffuse > 0, f"阴天漫射辐照度应>0, 实际{diffuse:.1f}"
            record_result("CIE阴天模型(配置驱动)", True)
        except Exception as e:
            record_result("CIE阴天模型(配置驱动)", False, str(e))

        try:
            perez = PerezSkyModel(params, config=config.get('perez'))
            zenith_lum = perez.get_sky_luminance(0, 0)
            assert zenith_lum > 0, f"Perez天顶亮度应>0, 实际{zenith_lum:.1f}"
            record_result("Perez模型(配置驱动)", True)
        except Exception as e:
            record_result("Perez模型(配置驱动)", False, str(e))

    def test_lighting_calc_with_config(self):
        """测试光照计算器使用JSON配置"""
        logger.info("=== 9. 光照计算器(配置驱动)测试 ===")

        try:
            from shared.config import load_json_config
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'daylight_simulator'))
            from simulation.lighting_calc import BuildingGeometry, LightingCalculator

            config = load_json_config("optical_params.json")

            geo = BuildingGeometry.from_config(config.get('building', {}))
            assert geo.length == 20.0, f"建筑长度应为20, 实际{geo.length}"
            assert geo.width == 20.0
            assert len(geo.windows) >= 4, f"至少4扇窗户, 实际{len(geo.windows)}"
            record_result("BuildingGeometry.from_config", True)
        except Exception as e:
            record_result("BuildingGeometry.from_config", False, str(e))

        try:
            from shared.config import load_json_config
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'daylight_simulator'))
            from simulation.lighting_calc import LightingCalculator
            from simulation.sky_model import create_sky_model, SkyModelParameters

            opt_config = load_json_config("optical_params.json")
            sky_config = load_json_config("sky_model_params.json")

            params = SkyModelParameters(solar_altitude=45.0, solar_azimuth=180.0, turbidity=2.5)

            geo = BuildingGeometry.from_config(opt_config.get('building', {}))
            calculator = LightingCalculator(
                building=geo,
                latitude=34.2658,
                longitude=108.9541,
            )

            result = calculator.calculate_illuminance(
                dt=datetime(2024, 6, 21, 12, 0, 0),
                sky_model_type='perez',
                turbidity=2.5
            )
            assert result.avg_illuminance > 0, f"平均照度应>0, 实际{result.avg_illuminance:.1f}"
            assert 0 < result.uniformity <= 1, f"均匀度应在(0,1], 实际{result.uniformity:.4f}"
            record_result("LightingCalculator(配置驱动)全流程", True)
        except Exception as e:
            record_result("LightingCalculator(配置驱动)全流程", False, str(e))

    def test_pso_optimizer_with_config(self):
        """测试PSO优化器使用JSON配置"""
        logger.info("=== 10. PSO优化器(配置驱动)测试 ===")

        try:
            from shared.config import load_json_config
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sunlight_optimizer'))
            from optimization.pso_optimizer import ParticleSwarmOptimizer

            opt_config = load_json_config("optimizer_params.json")

            def dummy_fitness(params):
                import numpy as np
                vals = []
                for p in params:
                    if hasattr(p, 'position'):
                        if isinstance(p.position, np.ndarray):
                            vals.extend(p.position.tolist())
                        elif isinstance(p.position, (list, tuple)):
                            vals.extend(p.position)
                        else:
                            vals.append(float(p.position))
                    if hasattr(p, 'size'):
                        if isinstance(p.size, np.ndarray):
                            vals.extend(p.size.tolist())
                        elif isinstance(p.size, (list, tuple)):
                            vals.extend(p.size)
                    if hasattr(p, 'transmittance'):
                        vals.append(float(p.transmittance))
                arr = np.array(vals)
                uniformity = float(0.5 + 0.3 * (arr.mean() % 1.0))
                avg_ill = float(300 + 200 * abs(arr.sum() % 1000) / 100.0)
                window_eff = float(0.5 + 0.3 * min(float(arr.std()), 1.0))
                return uniformity, avg_ill, window_eff

            optimizer = ParticleSwarmOptimizer(
                fitness_function=dummy_fitness,
                num_windows=4,
                population_size=10,
                max_iterations=5,
                config_override=opt_config,
                random_seed=42
            )

            result = optimizer.optimize()
            assert result.uniformity > 0, "均匀度应>0"
            assert result.avg_illuminance > 0, "平均照度应>0"
            record_result("PSO优化器(配置驱动)基础运行", True)
        except Exception as e:
            record_result("PSO优化器(配置驱动)基础运行", False, str(e))

        try:
            from shared.config import load_json_config
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sunlight_optimizer'))
            from optimization.pso_optimizer import ParticleSwarmOptimizer

            opt_config = load_json_config("optimizer_params.json")

            def dummy_fitness_mo(params):
                import numpy as np
                vals = []
                for p in params:
                    if hasattr(p, 'position'):
                        if isinstance(p.position, np.ndarray):
                            vals.extend(p.position.tolist())
                        elif isinstance(p.position, (list, tuple)):
                            vals.extend(p.position)
                        else:
                            vals.append(float(p.position))
                    if hasattr(p, 'size'):
                        if isinstance(p.size, np.ndarray):
                            vals.extend(p.size.tolist())
                        elif isinstance(p.size, (list, tuple)):
                            vals.extend(p.size)
                    if hasattr(p, 'transmittance'):
                        vals.append(float(p.transmittance))
                arr = np.array(vals)
                uniformity = float(0.5 + 0.3 * (arr.mean() % 1.0))
                avg_ill = float(300 + 200 * abs(arr.sum() % 1000) / 100.0)
                window_eff = float(0.5 + 0.3 * min(float(arr.std()), 1.0))
                return uniformity, avg_ill, window_eff

            optimizer_mo = ParticleSwarmOptimizer(
                fitness_function=dummy_fitness_mo,
                num_windows=6,
                population_size=10,
                max_iterations=5,
                use_multi_objective=True,
                config_override=opt_config,
                random_seed=42
            )

            result_mo = optimizer_mo.optimize()
            assert len(result_mo.pareto_front) >= 1, "Pareto前沿至少1个解"
            record_result("PSO多目标优化(配置驱动)", True)
        except Exception as e:
            record_result("PSO多目标优化(配置驱动)", False, str(e))

    def test_redis_pub_sub(self):
        """测试Redis Pub/Sub通信"""
        logger.info("=== 11. Redis Pub/Sub测试 ===")

        if not HAS_REDIS:
            record_skip("Redis Pub/Sub", "redis包未安装")
            return

        try:
            r = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                db=0,
                decode_responses=True
            )
            r.ping()
        except Exception:
            record_skip("Redis Pub/Sub", "Redis服务未启动")
            return

        received_messages = []

        def subscriber_thread():
            pubsub = r.pubsub()
            pubsub.subscribe("test:regression")
            for msg in pubsub.listen():
                if msg['type'] == 'message':
                    received_messages.append(msg['data'])
                    if len(received_messages) >= 2:
                        break
            pubsub.unsubscribe()
            pubsub.close()

        t = threading.Thread(target=subscriber_thread, daemon=True)
        t.start()
        time.sleep(0.5)

        test_msg = json.dumps({"test": "sensor_data", "value": 123.45})
        r.publish("test:regression", test_msg)
        test_msg2 = json.dumps({"test": "alert", "value": 67.89})
        r.publish("test:regression", test_msg2)

        t.join(timeout=5)

        if len(received_messages) >= 2:
            record_result("Redis Pub/Sub消息收发", True)
        else:
            record_result("Redis Pub/Sub消息收发", False, f"只收到{len(received_messages)}条消息")

        try:
            r.delete("test:regression")
        except Exception:
            pass

    def test_microservice_main_import(self):
        """测试四个微服务主模块可导入"""
        logger.info("=== 12. 微服务主模块导入测试 ===")

        services = [
            ('dtu_receiver.main', os.path.join(os.path.dirname(__file__), '..', 'dtu_receiver')),
            ('daylight_simulator.main', os.path.join(os.path.dirname(__file__), '..', 'daylight_simulator')),
            ('sunlight_optimizer.main', os.path.join(os.path.dirname(__file__), '..', 'sunlight_optimizer')),
            ('alarm_mqtt.main', os.path.join(os.path.dirname(__file__), '..', 'alarm_mqtt')),
        ]

        for module_name, module_dir in services:
            try:
                if module_dir not in sys.path:
                    sys.path.insert(0, module_dir)
                import importlib
                mod = importlib.import_module(module_name)
                assert hasattr(mod, 'app'), f"{module_name}缺少app对象"
                record_result(f"微服务导入: {module_name}", True)
            except Exception as e:
                record_result(f"微服务导入: {module_name}", False, str(e))

    def run_all(self):
        logger.info("=" * 60)
        logger.info("明堂采光仿真系统 — 微服务拆分功能回归测试")
        logger.info("=" * 60)

        self.test_json_config_files()
        self.test_sky_model_params()
        self.test_optical_params()
        self.test_optimizer_params()
        self.test_alarm_params()
        self.test_shared_schemas()
        self.test_shared_config()
        self.test_sky_model_with_config()
        self.test_lighting_calc_with_config()
        self.test_pso_optimizer_with_config()
        self.test_redis_pub_sub()
        self.test_microservice_main_import()

        logger.info("=" * 60)
        logger.info(f"测试结果: ✅ {PASS_COUNT} 通过 | ❌ {FAIL_COUNT} 失败 | ⏭️ {SKIP_COUNT} 跳过")
        logger.info("=" * 60)

        if FAIL_COUNT > 0:
            logger.error("存在失败用例，请检查！")
            return 1
        return 0


if __name__ == '__main__':
    suite = RegressionTestSuite()
    exit(suite.run_all())
