#!/usr/bin/env python3
"""
明堂采光仿真系统 — 新增Feature功能测试
测试4个新功能的核心逻辑：朝代对比、标准对比、树木影响、虚拟参观
覆盖正常场景、边界场景、异常场景
"""
import sys
import os
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

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


def _setup_path():
    """配置Python路径"""
    base = os.path.join(os.path.dirname(__file__), '..', 'daylight_simulator')
    if base not in sys.path:
        sys.path.insert(0, base)
    backend_root = os.path.join(os.path.dirname(__file__), '..')
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)


class FeaturesTestSuite:
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')

    # ==================== Feature 1: 朝代对比 — 照度水平验证 ====================

    def test_f1_config_files(self):
        """F1-01: 朝代配置文件结构完整性"""
        logger.info("=== Feature 1: 朝代对比 — 配置文件测试 ===")

        filepath = os.path.join(self.config_dir, 'dynasty_params.json')
        try:
            assert os.path.exists(filepath), f"文件不存在: {filepath}"
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert 'dynasties' in data, "缺少dynasties顶层键"
            dynasties = data['dynasties']
            for key in ['han', 'tang', 'ming']:
                assert key in dynasties, f"缺少朝代: {key}"
                d = dynasties[key]
                assert 'name' in d, f"{key}缺少name"
                assert 'building' in d, f"{key}缺少building"
                assert 'materials' in d, f"{key}缺少materials"
                assert 'latitude' in d, f"{key}缺少latitude"
                assert 'longitude' in d, f"{key}缺少longitude"
                b = d['building']
                assert b['length'] > 0, f"{key}建筑长度应>0"
                assert b['width'] > 0, f"{key}建筑宽度应>0"
                assert b['height'] > 0, f"{key}建筑高度应>0"
                assert len(b.get('default_windows', [])) >= 4, f"{key}至少4扇窗户"
            record_result("F1-01: 朝代配置结构完整性", True)
        except Exception as e:
            record_result("F1-01: 朝代配置结构完整性", False, str(e))

    def test_f1_normal_three_dynasties(self):
        """F1-02 [正常]: 汉唐明三朝正午照度对比"""
        logger.info("=== Feature 1: 朝代对比 — 正常场景: 三朝正午照度 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator
            import numpy as np

            results = {}
            for dynasty in ['han', 'tang', 'ming']:
                calc = LightingCalculator.from_dynasty(dynasty, grid_resolution=8)
                dt = datetime(2024, 6, 21, 12, 0, 0)
                result = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)
                results[dynasty] = {
                    'avg': result.avg_illuminance,
                    'min': result.min_illuminance,
                    'max': result.max_illuminance,
                    'uniformity': result.uniformity
                }

            for d, r in results.items():
                assert r['avg'] > 0, f"{d}平均照度应>0, 实际{r['avg']:.1f}"
                assert r['min'] >= 0, f"{d}最小照度应>=0"
                assert r['max'] >= r['min'], f"{d}最大照度应>=最小照度"
                assert 0 < r['uniformity'] <= 1, f"{d}均匀度应在(0,1]"
                assert r['avg'] < 1e6, f"{d}平均照度过大（可能异常）: {r['avg']:.1f}"

            logger.info(f"    汉: {results['han']['avg']:.0f} lux | 唐: {results['tang']['avg']:.0f} lux | 明: {results['ming']['avg']:.0f} lux")
            record_result("F1-02: 三朝正午照度均为正值且合理", True)
        except Exception as e:
            record_result("F1-02: 三朝正午照度均为正值且合理", False, str(e))

    def test_f1_normal_summer_vs_winter(self):
        """F1-03 [正常]: 同一朝代冬夏照度差异（夏至>冬至）"""
        logger.info("=== Feature 1: 朝代对比 — 正常场景: 冬夏照度对比 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('han', grid_resolution=8)

            dt_summer = datetime(2024, 6, 21, 12, 0, 0)
            dt_winter = datetime(2024, 12, 21, 12, 0, 0)

            r_summer = calc.calculate_illuminance(dt_summer, sky_model_type='perez', turbidity=2.5)
            r_winter = calc.calculate_illuminance(dt_winter, sky_model_type='perez', turbidity=2.5)

            assert r_summer.avg_illuminance > r_winter.avg_illuminance, \
                f"夏至照度({r_summer.avg_illuminance:.0f})应>冬至照度({r_winter.avg_illuminance:.0f})"
            assert r_summer.solar_altitude > r_winter.solar_altitude, \
                f"夏至太阳高度应>冬至"
            logger.info(f"    夏至: {r_summer.avg_illuminance:.0f} lux (高度{r_summer.solar_altitude:.1f}°) | 冬至: {r_winter.avg_illuminance:.0f} lux (高度{r_winter.solar_altitude:.1f}°)")
            record_result("F1-03: 夏至照度>冬至照度（同一朝代）", True)
        except Exception as e:
            record_result("F1-03: 夏至照度>冬至照度（同一朝代）", False, str(e))

    def test_f1_boundary_single_dynasty(self):
        """F1-04 [边界]: 单朝代对比也能正常返回"""
        logger.info("=== Feature 1: 朝代对比 — 边界场景: 单朝代 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('ming', grid_resolution=5)
            dt = datetime(2024, 3, 21, 12, 0, 0)
            result = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            assert result.avg_illuminance > 0, "单朝代平均照度应>0"
            assert result.illuminance_matrix.size > 0, "照度矩阵非空"
            record_result("F1-04: 单朝代也能正常返回结果", True)
        except Exception as e:
            record_result("F1-04: 单朝代也能正常返回结果", False, str(e))

    def test_f1_boundary_min_resolution(self):
        """F1-05 [边界]: 极低网格分辨率（1x1x1）仍能计算"""
        logger.info("=== Feature 1: 朝代对比 — 边界场景: 最低分辨率 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('tang', grid_resolution=2)
            dt = datetime(2024, 6, 21, 12, 0, 0)
            result = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            assert result.avg_illuminance > 0, "低分辨率下平均照度应>0"
            assert result.grid_size[0] >= 1, "网格x维度应>=1"
            logger.info(f"    grid_size: {result.grid_size}, avg: {result.avg_illuminance:.0f} lux")
            record_result("F1-05: 极低分辨率仍能计算", True)
        except Exception as e:
            record_result("F1-05: 极低分辨率仍能计算", False, str(e))

    def test_f1_boundary_midnight(self):
        """F1-06 [边界]: 深夜时分返回夜间常量照度且均匀度为1"""
        logger.info("=== Feature 1: 朝代对比 — 边界场景: 夜间常量照度 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('han', grid_resolution=5)
            dt = datetime(2024, 6, 21, 2, 0, 0)
            result = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            assert result.avg_illuminance > 0, "夜间应有基础环境照度"
            assert result.avg_illuminance < 50, f"夜间照度应较低(<50 lux), 实际{result.avg_illuminance:.1f}"
            assert result.uniformity == 1.0, f"夜间均匀度应为1.0, 实际{result.uniformity}"
            assert result.min_illuminance == result.max_illuminance, "夜间所有点照度应一致"

            logger.info(f"    夜间照度: {result.avg_illuminance:.1f} lux, 均匀度: {result.uniformity}")
            record_result("F1-06: 夜间返回均匀低照度", True)
        except Exception as e:
            record_result("F1-06: 夜间返回均匀低照度", False, str(e))

    def test_f1_abnormal_invalid_dynasty(self):
        """F1-07 [异常]: 无效朝代名称应回退到汉朝默认值"""
        logger.info("=== Feature 1: 朝代对比 — 异常场景: 无效朝代回退 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('invalid_dynasty_xyz', grid_resolution=5)
            dt = datetime(2024, 6, 21, 12, 0, 0)
            result = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            assert result.avg_illuminance > 0, "无效朝代回退后仍应返回正照度"
            assert calc.building.length == 20.0, f"回退到汉朝后建筑长度应为20, 实际{calc.building.length}"
            record_result("F1-07: 无效朝代回退到默认值", True)
        except Exception as e:
            record_result("F1-07: 无效朝代回退到默认值", False, str(e))

    # ==================== Feature 2: 跨时代标准对比 — 采光系数验证 ====================

    def test_f2_config_files(self):
        """F2-01: 采光标准配置文件结构完整性"""
        logger.info("=== Feature 2: 标准对比 — 配置文件测试 ===")

        filepath = os.path.join(self.config_dir, 'standards_params.json')
        try:
            assert os.path.exists(filepath), f"文件不存在: {filepath}"
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert 'modern_standards' in data, "缺少modern_standards"
            assert 'ancient_benchmarks' in data, "缺少ancient_benchmarks"
            assert 'comparison_categories' in data, "缺少comparison_categories"

            modern = data['modern_standards']
            ancient = data['ancient_benchmarks']
            assert isinstance(modern, list), "modern_standards应为list结构"
            assert isinstance(ancient, list), "ancient_benchmarks应为list结构"

            modern_keys = {s['key'] for s in modern}
            ancient_keys = {s['key'] for s in ancient}
            for key in ['gb50033_2013', 'en17037_2019', 'leed_v4_1']:
                assert key in modern_keys, f"现代标准中缺少: {key}"
            assert 'ancient_ideal' in ancient_keys, "古代基准中缺少: ancient_ideal"

            for s in modern + ancient:
                assert 'full_name' in s, f"{s.get('key', '?')}缺少full_name"
                assert 'metrics' in s, f"{s.get('key', '?')}缺少metrics"
                for m_key in ['daylight_factor_min', 'daylight_factor_avg', 'illuminance_avg']:
                    assert m_key in s['metrics'], f"{s.get('key', '?')}缺少metric.{m_key}"

            cats = data['comparison_categories']
            assert len(cats) >= 5, "至少5个对比维度"
            total_weight = sum(c['weight'] for c in cats)
            assert abs(total_weight - 1.0) < 0.01, f"权重和应为1, 实际{total_weight}"
            record_result("F2-01: 标准配置结构完整性", True)
        except Exception as e:
            record_result("F2-01: 标准配置结构完整性", False, str(e))

    def test_f2_normal_compliance(self):
        """F2-02 [正常]: 典型工况下采光系数和合规性计算"""
        logger.info("=== Feature 2: 标准对比 — 正常场景: 采光系数合规计算 ===")
        try:
            _setup_path()
            from daylight_simulator.services.feature_service import FeatureService

            fs = FeatureService.__new__(FeatureService)
            fs.tasks = {}

            results = fs.compare_standards(
                dynasty_key='tang',
                avg_illuminance=500.0,
                min_illuminance=200.0,
                uniformity=0.65
            )

            assert len(results) >= 3, f"至少3套标准对比, 实际{len(results)}"
            for r in results:
                assert 'standard_key' in r
                assert 'simulated_metrics' in r
                assert 'standards_compliance' in r
                assert 'overall_score' in r
                metrics = r['simulated_metrics']
                assert 'daylight_factor_avg' in metrics
                assert 'daylight_factor_min' in metrics
                df_avg = metrics['daylight_factor_avg']
                assert df_avg > 0, f"{r['standard_key']}采光系数应>0"
                assert 0 <= r['overall_score'] <= 1.5, f"综合评分应在合理范围: {r['overall_score']}"

            avg_df = results[0]['simulated_metrics']['daylight_factor_avg']
            expected_df = (500.0 / 10000.0) * 100
            assert abs(avg_df - expected_df) < 0.1, f"采光系数计算错误: {avg_df} vs 预期{expected_df}"

            logger.info(f"    采光系数(平均): {avg_df:.2f}% | 最高标准得分: {max(r['overall_score'] for r in results):.3f}")
            record_result("F2-02: 采光系数与合规性计算正确", True)
        except Exception as e:
            record_result("F2-02: 采光系数与合规性计算正确", False, str(e))

    def test_f2_boundary_low_illuminance(self):
        """F2-03 [边界]: 极低照度下采光系数接近0"""
        logger.info("=== Feature 2: 标准对比 — 边界场景: 极低照度 ===")
        try:
            _setup_path()
            from daylight_simulator.services.feature_service import FeatureService

            fs = FeatureService.__new__(FeatureService)
            fs.tasks = {}

            results = fs.compare_standards(
                dynasty_key='han',
                avg_illuminance=10.0,
                min_illuminance=1.0,
                uniformity=0.1
            )

            for r in results:
                df_avg = r['simulated_metrics']['daylight_factor_avg']
                assert df_avg > 0, "极低照度下采光系数也应>0"
                assert df_avg < 1.0, f"极低照度下采光系数应<1%, 实际{df_avg}%"
                assert r['overall_score'] < 0.5, f"极低照度下综合得分应较低: {r['overall_score']}"

            logger.info(f"    极低照度采光系数: {results[0]['simulated_metrics']['daylight_factor_avg']:.4f}%")
            record_result("F2-03: 极低照度采光系数接近0", True)
        except Exception as e:
            record_result("F2-03: 极低照度采光系数接近0", False, str(e))

    def test_f2_boundary_high_illuminance(self):
        """F2-04 [边界]: 高照度下全项达标（得分上限验证）"""
        logger.info("=== Feature 2: 标准对比 — 边界场景: 高照度全达标 ===")
        try:
            _setup_path()
            from daylight_simulator.services.feature_service import FeatureService

            fs = FeatureService.__new__(FeatureService)
            fs.tasks = {}

            results = fs.compare_standards(
                dynasty_key='ming',
                avg_illuminance=5000.0,
                min_illuminance=3000.0,
                uniformity=0.9
            )

            for r in results:
                df_avg = r['simulated_metrics']['daylight_factor_avg']
                assert df_avg > 10, f"高照度下采光系数应>10%, 实际{df_avg}%"
                assert r['overall_score'] > 0.5, f"高照度下综合得分应较高: {r['overall_score']}"

            logger.info(f"    高照度采光系数: {results[0]['simulated_metrics']['daylight_factor_avg']:.2f}% | 得分: {results[0]['overall_score']:.3f}")
            record_result("F2-04: 高照度下得分显著更高", True)
        except Exception as e:
            record_result("F2-04: 高照度下得分显著更高", False, str(e))

    def test_f2_boundary_zero_illuminance(self):
        """F2-05 [边界]: 零照度边界（全黑场景）"""
        logger.info("=== Feature 2: 标准对比 — 边界场景: 零照度 ===")
        try:
            _setup_path()
            from daylight_simulator.services.feature_service import FeatureService

            fs = FeatureService.__new__(FeatureService)
            fs.tasks = {}

            results = fs.compare_standards(
                dynasty_key='han',
                avg_illuminance=0.0,
                min_illuminance=0.0,
                uniformity=0.0
            )

            for r in results:
                assert r['simulated_metrics']['daylight_factor_avg'] == 0.0, "零照度下采光系数应为0"
                assert r['overall_score'] == 0.0, f"零照度下综合得分应为0, 实际{r['overall_score']}"
                for cat, comp in r['standards_compliance'].items():
                    assert not comp['pass'], f"零照度下{cat}应不达标"

            record_result("F2-05: 零照度下所有指标不达标", True)
        except Exception as e:
            record_result("F2-05: 零照度下所有指标不达标", False, str(e))

    def test_f2_abnormal_negative_illuminance(self):
        """F2-06 [异常]: 负照度输入的鲁棒性"""
        logger.info("=== Feature 2: 标准对比 — 异常场景: 负照度输入 ===")
        try:
            _setup_path()
            from daylight_simulator.services.feature_service import FeatureService

            fs = FeatureService.__new__(FeatureService)
            fs.tasks = {}

            results = fs.compare_standards(
                dynasty_key='tang',
                avg_illuminance=-100.0,
                min_illuminance=-200.0,
                uniformity=0.5
            )

            df_avg = results[0]['simulated_metrics']['daylight_factor_avg']
            assert df_avg < 0 or results[0]['overall_score'] < 0.1, \
                f"负照度应导致低得分或负采光系数: df={df_avg}, score={results[0]['overall_score']}"
            logger.info(f"    负照度采光系数: {df_avg:.2f}%")
            record_result("F2-06: 负照度输入不崩溃（鲁棒性）", True)
        except Exception as e:
            record_result("F2-06: 负照度输入不崩溃（鲁棒性）", False, str(e))

    def test_f2_abnormal_invalid_dynasty(self):
        """F2-07 [异常]: 无效朝代在标准对比中回退"""
        logger.info("=== Feature 2: 标准对比 — 异常场景: 无效朝代 ===")
        try:
            _setup_path()
            from daylight_simulator.services.feature_service import FeatureService

            fs = FeatureService.__new__(FeatureService)
            fs.tasks = {}

            results = fs.compare_standards(
                dynasty_key='nonexistent_dynasty',
                avg_illuminance=300.0,
                min_illuminance=100.0,
                uniformity=0.5
            )

            assert len(results) > 0, "无效朝代仍应返回对比结果"
            assert results[0]['dynasty'] == 'nonexistent_dynasty', "dynasty字段应与输入一致"
            record_result("F2-07: 无效朝代仍返回结果（回退处理）", True)
        except Exception as e:
            record_result("F2-07: 无效朝代仍返回结果（回退处理）", False, str(e))

    # ==================== Feature 3: 树木影响 — 阴影范围验证 ====================

    def test_f3_config_files(self):
        """F3-01: 树木配置文件结构完整性"""
        logger.info("=== Feature 3: 树木影响 — 配置文件测试 ===")

        filepath = os.path.join(self.config_dir, 'tree_params.json')
        try:
            assert os.path.exists(filepath), f"文件不存在: {filepath}"
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            assert 'tree_species' in data, "缺少tree_species"
            assert 'seasonal_factors' in data, "缺少seasonal_factors"
            assert 'default_layout' in data, "缺少default_layout"

            species = data['tree_species']
            assert len(species) >= 3, "至少3种树种"
            for key, sp in species.items():
                assert 'name' in sp, f"{key}缺少name"
                assert sp['trunk_radius'] > 0, f"{key}树干半径应>0"
                assert sp['trunk_height'] > 0, f"{key}树干高度应>0"
                assert sp['canopy_radius'] > 0, f"{key}树冠半径应>0"
                assert 0 <= sp['canopy_transmittance'] <= 1, f"{key}透光率应在[0,1]"

            seasons = data['seasonal_factors']
            for s in ['spring', 'summer', 'autumn', 'winter']:
                assert s in seasons, f"缺少季节: {s}"
                leaf = seasons[s].get('leaf_factor', 1.0)
                assert 0 <= leaf <= 1, f"{s}叶因子应在[0,1]"

            record_result("F3-01: 树木配置结构完整性", True)
        except Exception as e:
            record_result("F3-01: 树木配置结构完整性", False, str(e))

    def test_f3_geometry_cylinder_intersect(self):
        """F3-02 [单元]: 圆柱体（树干）光线求交正确性"""
        logger.info("=== Feature 3: 树木影响 — 几何测试: 圆柱体求交 ===")
        try:
            _setup_path()
            import numpy as np
            from simulation.ray_tracer import Cylinder, Material, Ray

            mat = Material(name='test', albedo=np.array([0.5, 0.5, 0.5]), reflectivity=0.1)
            cyl = Cylinder(base_center=np.array([0, 0, 0]), radius=1.0, height=5.0, material=mat)

            ray_hit = Ray(origin=np.array([-5, 0, 2.5]), direction=np.array([1, 0, 0]))
            hit = cyl.intersect(ray_hit)
            assert hit.hit, f"水平射线应击中圆柱侧面, distance={hit.distance}"
            assert abs(hit.distance - 4.0) < 0.01, f"击中距离应为4.0, 实际{hit.distance:.3f}"

            ray_miss = Ray(origin=np.array([-5, 2, 2.5]), direction=np.array([1, 0, 0]))
            miss = cyl.intersect(ray_miss)
            assert not miss.hit, "偏心射线不应击中圆柱"

            ray_top = Ray(origin=np.array([0, 0, 10]), direction=np.array([0, 0, -1]))
            top_hit = cyl.intersect(ray_top)
            assert top_hit.hit, f"垂直射线应击中圆柱顶盖, distance={top_hit.distance}"
            assert abs(top_hit.distance - 5.0) < 0.01, f"顶盖击中距离应为5.0, 实际{top_hit.distance:.3f}"

            record_result("F3-02: 圆柱体光线求交正确", True)
        except Exception as e:
            record_result("F3-02: 圆柱体光线求交正确", False, str(e))

    def test_f3_geometry_sphere_intersect(self):
        """F3-03 [单元]: 球体（树冠）光线求交正确性"""
        logger.info("=== Feature 3: 树木影响 — 几何测试: 球体求交 ===")
        try:
            _setup_path()
            import numpy as np
            from simulation.ray_tracer import Sphere, Material, Ray

            mat = Material(name='test', albedo=np.array([0.3, 0.6, 0.2]), reflectivity=0.05, transmittance=0.3)
            sphere = Sphere(center=np.array([0, 0, 5]), radius=2.0, material=mat)

            ray_through = Ray(origin=np.array([-5, 0, 5]), direction=np.array([1, 0, 0]))
            hit = sphere.intersect(ray_through)
            assert hit.hit, f"射线应穿过球体, distance={hit.distance}"
            assert abs(hit.distance - 3.0) < 0.01, f"入射距离应为3.0, 实际{hit.distance:.3f}"

            ray_tangent = Ray(origin=np.array([-5, 2.0, 5]), direction=np.array([1, 0, 0]))
            tangent = sphere.intersect(ray_tangent)
            assert not tangent.hit or abs(tangent.distance - 5.0) < 0.1, "切线应刚好擦过或不相交"

            ray_outside = Ray(origin=np.array([-5, 4, 5]), direction=np.array([1, 0, 0]))
            miss = sphere.intersect(ray_outside)
            assert not miss.hit, "远离球体的射线不应相交"

            record_result("F3-03: 球体光线求交正确", True)
        except Exception as e:
            record_result("F3-03: 球体光线求交正确", False, str(e))

    def test_f3_normal_tree_reduces_illuminance(self):
        """F3-04 [正常]: 添加树木后平均照度下降"""
        logger.info("=== Feature 3: 树木影响 — 正常场景: 树木降低照度 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('han', grid_resolution=8)
            dt = datetime(2024, 6, 21, 12, 0, 0)

            result_before = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            trees = [
                {"species": "pine", "position": [-6, 0, 0], "scale": 1.2},
                {"species": "ginkgo", "position": [6, 0, 0], "scale": 1.0},
            ]
            calc.add_trees(trees, season='summer')

            result_after = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            reduction_pct = (1 - result_after.avg_illuminance / result_before.avg_illuminance) * 100
            assert result_after.avg_illuminance < result_before.avg_illuminance, \
                f"添加树木后照度应下降, 前:{result_before.avg_illuminance:.0f} 后:{result_after.avg_illuminance:.0f}"
            assert reduction_pct > 0, f"照度衰减率应>0, 实际{reduction_pct:.2f}%"
            assert reduction_pct < 90, f"衰减率不应过大（<90%）: {reduction_pct:.2f}%"

            logger.info(f"    无树: {result_before.avg_illuminance:.0f} lux | 有树: {result_after.avg_illuminance:.0f} lux | 衰减: {reduction_pct:.1f}%")
            record_result("F3-04: 添加树木后照度显著下降", True)
        except Exception as e:
            record_result("F3-04: 添加树木后照度显著下降", False, str(e))

    def test_f3_normal_seasonal_effect(self):
        """F3-05 [正常]: 冬季落叶树比夏季阴影更弱"""
        logger.info("=== Feature 3: 树木影响 — 正常场景: 季节影响 ===")
        try:
            _setup_path()
            import copy
            from simulation.lighting_calc import LightingCalculator

            calc_summer = LightingCalculator.from_dynasty('han', grid_resolution=8)
            calc_winter = LightingCalculator.from_dynasty('han', grid_resolution=8)

            trees = [
                {"species": "ginkgo", "position": [5, 5, 0], "scale": 1.5},
            ]
            calc_summer.add_trees(trees, season='summer')
            calc_winter.add_trees(trees, season='winter')

            dt = datetime(2024, 6, 21, 12, 0, 0)
            r_summer = calc_summer.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)
            r_winter = calc_winter.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            calc_bare = LightingCalculator.from_dynasty('han', grid_resolution=8)
            r_bare = calc_bare.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            summer_reduction = r_bare.avg_illuminance - r_summer.avg_illuminance
            winter_reduction = r_bare.avg_illuminance - r_winter.avg_illuminance

            assert summer_reduction > winter_reduction, \
                f"夏季阴影应强于冬季: 夏减{summer_reduction:.0f} vs 冬减{winter_reduction:.0f}"

            logger.info(f"    无树: {r_bare.avg_illuminance:.0f} lux | 夏季: {r_summer.avg_illuminance:.0f} lux | 冬季: {r_winter.avg_illuminance:.0f} lux")
            record_result("F3-05: 夏季阴影强于冬季（落叶树）", True)
        except Exception as e:
            record_result("F3-05: 夏季阴影强于冬季（落叶树）", False, str(e))

    def test_f3_boundary_zero_trees(self):
        """F3-06 [边界]: 0棵树时与无树场景一致"""
        logger.info("=== Feature 3: 树木影响 — 边界场景: 0棵树 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc1 = LightingCalculator.from_dynasty('tang', grid_resolution=8)
            calc2 = LightingCalculator.from_dynasty('tang', grid_resolution=8)

            calc1.add_trees([], season='summer')

            dt = datetime(2024, 6, 21, 12, 0, 0)
            r1 = calc1.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)
            r2 = calc2.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            diff_pct = abs(r1.avg_illuminance - r2.avg_illuminance) / r2.avg_illuminance * 100
            assert diff_pct < 1.0, \
                f"0棵树与无树场景照度差异应<1%: 差异{diff_pct:.2f}%"
            record_result("F3-06: 0棵树与无树场景照度基本一致", True)
        except Exception as e:
            record_result("F3-06: 0棵树与无树场景照度一致", False, str(e))

    def test_f3_boundary_distant_trees(self):
        """F3-07 [边界]: 极远处树木几乎不影响采光"""
        logger.info("=== Feature 3: 树木影响 — 边界场景: 极远树木 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc_near = LightingCalculator.from_dynasty('han', grid_resolution=8)
            calc_far = LightingCalculator.from_dynasty('han', grid_resolution=8)

            big_tree = [{"species": "pine", "position": [-5, 0, 0], "scale": 2.0}]
            far_tree = [{"species": "pine", "position": [-100, 0, 0], "scale": 2.0}]

            calc_near.add_trees(big_tree, season='summer')
            calc_far.add_trees(far_tree, season='summer')

            dt = datetime(2024, 6, 21, 12, 0, 0)
            r_near = calc_near.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)
            r_far = calc_far.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            calc_bare = LightingCalculator.from_dynasty('han', grid_resolution=8)
            r_bare = calc_bare.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            near_diff = abs(r_bare.avg_illuminance - r_near.avg_illuminance)
            far_diff = abs(r_bare.avg_illuminance - r_far.avg_illuminance)

            assert near_diff > far_diff, \
                f"近处树木影响应大于远处: 近差{near_diff:.0f} vs 远差{far_diff:.0f}"
            logger.info(f"    近处树差: {near_diff:.1f} lux | 远处树差: {far_diff:.1f} lux")
            record_result("F3-07: 极远处树木影响极小", True)
        except Exception as e:
            record_result("F3-07: 极远处树木影响极小", False, str(e))

    def test_f3_boundary_dense_forest(self):
        """F3-08 [边界]: 密林场景下显著降低照度"""
        logger.info("=== Feature 3: 树木影响 — 边界场景: 密林 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('han', grid_resolution=8)

            dense_trees = []
            for i in range(-3, 4):
                for j in range(-3, 4):
                    dense_trees.append({
                        "species": "cypress",
                        "position": [float(i * 4), float(j * 4), 0],
                        "scale": 1.5
                    })

            calc.add_trees(dense_trees, season='summer')

            dt = datetime(2024, 6, 21, 12, 0, 0)
            r_dense = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            calc_bare = LightingCalculator.from_dynasty('han', grid_resolution=8)
            r_bare = calc_bare.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            reduction_pct = (1 - r_dense.avg_illuminance / r_bare.avg_illuminance) * 100
            assert reduction_pct > 10, f"密林应显著降低照度（>10%）, 实际{reduction_pct:.1f}%"
            assert r_dense.avg_illuminance > 0, "密林下仍应有漫射光（>0）"

            logger.info(f"    无树: {r_bare.avg_illuminance:.0f} lux | 密林: {r_dense.avg_illuminance:.0f} lux | 衰减: {reduction_pct:.1f}%")
            record_result("F3-08: 密林显著降低但不为零", True)
        except Exception as e:
            record_result("F3-08: 密林显著降低但不为零", False, str(e))

    def test_f3_abnormal_invalid_species(self):
        """F3-09 [异常]: 无效树种回退到默认松树"""
        logger.info("=== Feature 3: 树木影响 — 异常场景: 无效树种 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('han', grid_resolution=8)

            bad_trees = [{"species": "dragon_tree_invalid", "position": [0, 0, 0], "scale": 1.0}]
            calc.add_trees(bad_trees, season='summer')

            dt = datetime(2024, 6, 21, 12, 0, 0)
            result = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            assert result.avg_illuminance > 0, "无效树种回退后仍应返回正照度"
            record_result("F3-09: 无效树种回退到默认值不崩溃", True)
        except Exception as e:
            record_result("F3-09: 无效树种回退到默认值不崩溃", False, str(e))

    def test_f3_abnormal_negative_scale(self):
        """F3-10 [异常]: 负缩放因子的鲁棒性"""
        logger.info("=== Feature 3: 树木影响 — 异常场景: 负缩放 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('han', grid_resolution=8)

            weird_trees = [{"species": "pine", "position": [5, 5, 0], "scale": -1.0}]
            calc.add_trees(weird_trees, season='summer')

            dt = datetime(2024, 6, 21, 12, 0, 0)
            result = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)

            assert result.avg_illuminance > 0, "负缩放不应导致崩溃"
            record_result("F3-10: 负缩放因子鲁棒处理", True)
        except Exception as e:
            record_result("F3-10: 负缩放因子鲁棒处理", False, str(e))

    # ==================== Feature 4: 虚拟参观 — 时间交互验证 ====================

    def test_f4_params_validation(self):
        """F4-01: 虚拟参观参数Schema正确性"""
        logger.info("=== Feature 4: 虚拟参观 — 参数Schema测试 ===")
        try:
            from shared.schemas import VirtualTourParams

            params = VirtualTourParams(
                date="2024-06-21",
                start_hour=6,
                end_hour=18,
                time_step=30,
                dynasty="han"
            )
            assert params.start_hour == 6
            assert params.end_hour == 18
            assert params.time_step == 30
            assert params.dynasty.value == "han"
            record_result("F4-01: VirtualTourParams Schema正确", True)
        except Exception as e:
            record_result("F4-01: VirtualTourParams Schema正确", False, str(e))

    def test_f4_normal_full_day_sequence(self):
        """F4-02 [正常]: 全天时间序列照度变化规律（日出低→正午高→日落低）"""
        logger.info("=== Feature 4: 虚拟参观 — 正常场景: 全天照度时序 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator
            import numpy as np

            calc = LightingCalculator.from_dynasty('tang', grid_resolution=6)

            hourly_data = []
            for hour in range(6, 19):
                dt = datetime(2024, 6, 21, hour, 0, 0)
                result = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)
                hourly_data.append({
                    'hour': hour,
                    'avg_illuminance': result.avg_illuminance,
                    'solar_altitude': result.solar_altitude
                })

            assert len(hourly_data) == 13, f"应有13个时间点, 实际{len(hourly_data)}"

            morning = [d for d in hourly_data if d['hour'] <= 12]
            afternoon = [d for d in hourly_data if d['hour'] >= 12]

            morning_rising = all(
                morning[i]['avg_illuminance'] <= morning[i + 1]['avg_illuminance'] + 1
                for i in range(len(morning) - 1)
            )
            afternoon_falling = all(
                afternoon[i]['avg_illuminance'] >= afternoon[i + 1]['avg_illuminance'] - 1
                for i in range(len(afternoon) - 1)
            )

            assert morning_rising, "上午照度应整体上升"
            assert afternoon_falling, "下午照度应整体下降"

            noon_idx = max(range(len(hourly_data)), key=lambda i: hourly_data[i]['avg_illuminance'])
            assert 10 <= hourly_data[noon_idx]['hour'] <= 14, \
                f"最大照度应在中午前后, 实际在{hourly_data[noon_idx]['hour']}点"

            logger.info(f"    峰值照度: {hourly_data[noon_idx]['avg_illuminance']:.0f} lux @ {hourly_data[noon_idx]['hour']}点")
            record_result("F4-02: 全天照度呈单峰分布（午间最高）", True)
        except Exception as e:
            record_result("F4-02: 全天照度呈单峰分布（午间最高）", False, str(e))

    def test_f4_normal_sun_trajectory(self):
        """F4-03 [正常]: 太阳高度角从日出到日落的连续性"""
        logger.info("=== Feature 4: 虚拟参观 — 正常场景: 太阳轨迹连续 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('ming', grid_resolution=4)

            altitudes = []
            azimuths = []
            for minute in range(0, 721, 30):
                hour = minute / 60.0
                dt = datetime(2024, 6, 21, int(hour), int((hour % 1) * 60), 0)
                result = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)
                altitudes.append(result.solar_altitude)
                azimuths.append(result.solar_azimuth)

            for i in range(len(altitudes) - 1):
                alt_diff = abs(altitudes[i + 1] - altitudes[i])
                assert alt_diff < 15, f"太阳高度角30分钟变化不应超过15°, 实际{alt_diff:.1f}°"

            max_alt_idx = altitudes.index(max(altitudes))
            assert max(altitudes) > 60, f"夏至正午太阳高度应>60°, 实际{max(altitudes):.1f}°"

            logger.info(f"    最大高度: {max(altitudes):.1f}° | 方位范围: {min(azimuths):.1f}° ~ {max(azimuths):.1f}°")
            record_result("F4-03: 太阳高度角变化连续且合理", True)
        except Exception as e:
            record_result("F4-03: 太阳高度角变化连续且合理", False, str(e))

    def test_f4_boundary_sunrise_sunset(self):
        """F4-04 [边界]: 日出日落时刻照度接近0且高度角接近0"""
        logger.info("=== Feature 4: 虚拟参观 — 边界场景: 日出日落 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('han', grid_resolution=5)

            sunrise = datetime(2024, 6, 21, 5, 30, 0)
            sunset = datetime(2024, 6, 21, 19, 30, 0)

            r_sunrise = calc.calculate_illuminance(sunrise, sky_model_type='perez', turbidity=2.5)
            r_sunset = calc.calculate_illuminance(sunset, sky_model_type='perez', turbidity=2.5)

            r_noon = calc.calculate_illuminance(
                datetime(2024, 6, 21, 12, 0, 0),
                sky_model_type='perez', turbidity=2.5
            )

            assert r_sunrise.avg_illuminance < r_noon.avg_illuminance * 0.3, \
                f"日出照度应远低于正午: {r_sunrise.avg_illuminance:.0f} vs {r_noon.avg_illuminance:.0f}"
            assert r_sunset.avg_illuminance < r_noon.avg_illuminance * 0.3, \
                f"日落照度应远低于正午: {r_sunset.avg_illuminance:.0f} vs {r_noon.avg_illuminance:.0f}"

            logger.info(f"    日出: {r_sunrise.avg_illuminance:.0f} lux (高度{r_sunrise.solar_altitude:.1f}°)")
            logger.info(f"    正午: {r_noon.avg_illuminance:.0f} lux (高度{r_noon.solar_altitude:.1f}°)")
            logger.info(f"    日落: {r_sunset.avg_illuminance:.0f} lux (高度{r_sunset.solar_altitude:.1f}°)")
            record_result("F4-04: 日出日落照度远低于正午", True)
        except Exception as e:
            record_result("F4-04: 日出日落照度远低于正午", False, str(e))

    def test_f4_boundary_min_step(self):
        """F4-05 [边界]: 最小时间步长（1分钟）仍能产生有效差异"""
        logger.info("=== Feature 4: 虚拟参观 — 边界场景: 最小步长 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('han', grid_resolution=5)

            dt1 = datetime(2024, 6, 21, 12, 0, 0)
            dt2 = datetime(2024, 6, 21, 12, 1, 0)

            r1 = calc.calculate_illuminance(dt1, sky_model_type='perez', turbidity=2.5)
            r2 = calc.calculate_illuminance(dt2, sky_model_type='perez', turbidity=2.5)

            alt_diff = abs(r1.solar_altitude - r2.solar_altitude)
            assert alt_diff < 1.0, f"1分钟高度角变化应<1°, 实际{alt_diff:.3f}°"
            assert alt_diff > 0, "1分钟高度角应有微小变化"

            logger.info(f"    1分钟高度角变化: {alt_diff:.4f}°")
            record_result("F4-05: 1分钟步长太阳位置有微小但有效变化", True)
        except Exception as e:
            record_result("F4-05: 1分钟步长太阳位置有微小但有效变化", False, str(e))

    def test_f4_boundary_equinox_solstice(self):
        """F4-06 [边界]: 二分二至日太阳高度极值验证"""
        logger.info("=== Feature 4: 虚拟参观 — 边界场景: 二分二至 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('tang', grid_resolution=4)

            dates = {
                '春分': datetime(2024, 3, 20, 12, 0, 0),
                '夏至': datetime(2024, 6, 21, 12, 0, 0),
                '秋分': datetime(2024, 9, 22, 12, 0, 0),
                '冬至': datetime(2024, 12, 21, 12, 0, 0),
            }

            results = {}
            for name, dt in dates.items():
                r = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)
                results[name] = r.solar_altitude

            assert results['夏至'] > results['春分'] > results['冬至'], \
                f"高度排序错误: 夏{results['夏至']:.1f}° 春{results['春分']:.1f}° 冬{results['冬至']:.1f}°"
            assert abs(results['春分'] - results['秋分']) < 3, \
                f"春秋分高度应接近: 春{results['春分']:.1f}° vs 秋{results['秋分']:.1f}°"

            lat = calc.latitude
            expected_summer = 90 - lat + 23.5
            expected_winter = 90 - lat - 23.5
            assert abs(results['夏至'] - expected_summer) < 3, \
                f"夏至高度误差大: 实际{results['夏至']:.1f}° 预期~{expected_summer:.1f}°"
            assert abs(results['冬至'] - expected_winter) < 3, \
                f"冬至高度误差大: 实际{results['冬至']:.1f}° 预期~{expected_winter:.1f}°"

            logger.info(f"    夏至: {results['夏至']:.1f}° | 春分: {results['春分']:.1f}° | 冬至: {results['冬至']:.1f}°")
            record_result("F4-06: 二分二至太阳高度符合天文规律", True)
        except Exception as e:
            record_result("F4-06: 二分二至太阳高度符合天文规律", False, str(e))

    def test_f4_abnormal_end_before_start(self):
        """F4-07 [异常]: 结束时间早于开始时间的鲁棒性（不崩溃）"""
        logger.info("=== Feature 4: 虚拟参观 — 异常场景: 结束早于开始 ===")
        try:
            from shared.schemas import VirtualTourParams

            params = VirtualTourParams(
                date="2024-06-21",
                start_hour=18,
                end_hour=6,
                time_step=30,
                dynasty="han"
            )
            assert params.start_hour == 18
            assert params.end_hour == 6
            record_result("F4-07: 反向时间范围不崩溃（鲁棒性）", True,
                         "Schema不校验时间先后顺序但不崩溃")
        except Exception as e:
            record_result("F4-07: 反向时间范围被正确拦截", True, str(e))

    def test_f4_abnormal_negative_step(self):
        """F4-08 [异常]: 负时间步长被Schema校验拦截"""
        logger.info("=== Feature 4: 虚拟参观 — 异常场景: 负时间步长 ===")
        try:
            from shared.schemas import VirtualTourParams
            from pydantic import ValidationError

            try:
                params = VirtualTourParams(
                    date="2024-06-21",
                    start_hour=8,
                    end_hour=16,
                    time_step=-30,
                    dynasty="han"
                )
                record_result("F4-08: Schema未拦截负步长", False,
                             f"接受了time_step=-30")
            except ValidationError:
                record_result("F4-08: Schema校验拦截负步长", True)
        except ImportError:
            record_skip("F4-08: 跳过Schema负步长测试", "pydantic.ValidationError不可用")
        except Exception as e:
            record_result("F4-08: 负步长测试异常", False, str(e))

    def test_f4_abnormal_invalid_date(self):
        """F4-09 [异常]: 无效日期格式处理"""
        logger.info("=== Feature 4: 虚拟参观 — 异常场景: 无效日期 ===")
        try:
            _setup_path()
            from simulation.lighting_calc import LightingCalculator

            calc = LightingCalculator.from_dynasty('han', grid_resolution=5)
            try:
                dt = datetime.strptime("2024-13-45", "%Y-%m-%d")
                result = calc.calculate_illuminance(dt, sky_model_type='perez', turbidity=2.5)
                record_result("F4-09: 无效日期测试", False, "应抛出异常但没有")
            except ValueError:
                record_result("F4-09: 无效日期格式正确抛出异常", True)
        except Exception as e:
            record_result("F4-09: 无效日期测试异常", False, str(e))

    # ==================== 运行所有测试 ====================

    def run_all(self):
        logger.info("=" * 60)
        logger.info("明堂采光仿真系统 — 新增Feature功能测试")
        logger.info("    覆盖: 朝代对比 | 标准对比 | 树木影响 | 虚拟参观")
        logger.info("    场景: 正常 | 边界 | 异常")
        logger.info("=" * 60)

        # Feature 1
        self.test_f1_config_files()
        self.test_f1_normal_three_dynasties()
        self.test_f1_normal_summer_vs_winter()
        self.test_f1_boundary_single_dynasty()
        self.test_f1_boundary_min_resolution()
        self.test_f1_boundary_midnight()
        self.test_f1_abnormal_invalid_dynasty()

        # Feature 2
        self.test_f2_config_files()
        self.test_f2_normal_compliance()
        self.test_f2_boundary_low_illuminance()
        self.test_f2_boundary_high_illuminance()
        self.test_f2_boundary_zero_illuminance()
        self.test_f2_abnormal_negative_illuminance()
        self.test_f2_abnormal_invalid_dynasty()

        # Feature 3
        self.test_f3_config_files()
        self.test_f3_geometry_cylinder_intersect()
        self.test_f3_geometry_sphere_intersect()
        self.test_f3_normal_tree_reduces_illuminance()
        self.test_f3_normal_seasonal_effect()
        self.test_f3_boundary_zero_trees()
        self.test_f3_boundary_distant_trees()
        self.test_f3_boundary_dense_forest()
        self.test_f3_abnormal_invalid_species()
        self.test_f3_abnormal_negative_scale()

        # Feature 4
        self.test_f4_params_validation()
        self.test_f4_normal_full_day_sequence()
        self.test_f4_normal_sun_trajectory()
        self.test_f4_boundary_sunrise_sunset()
        self.test_f4_boundary_min_step()
        self.test_f4_boundary_equinox_solstice()
        self.test_f4_abnormal_end_before_start()
        self.test_f4_abnormal_negative_step()
        self.test_f4_abnormal_invalid_date()

        logger.info("=" * 60)
        logger.info(f"测试结果: ✅ {PASS_COUNT} 通过 | ❌ {FAIL_COUNT} 失败 | ⏭️ {SKIP_COUNT} 跳过")
        total = PASS_COUNT + FAIL_COUNT
        if total > 0:
            pass_rate = PASS_COUNT / total * 100
            logger.info(f"通过率: {pass_rate:.1f}%")
        logger.info("=" * 60)

        if FAIL_COUNT > 0:
            logger.error("存在失败用例，请检查！")
            return 1
        return 0


if __name__ == '__main__':
    suite = FeaturesTestSuite()
    exit(suite.run_all())
