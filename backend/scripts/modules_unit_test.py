#!/usr/bin/env python3
"""
新模块单元测试 — 针对重构后的4个独立功能模块和Worker进程
- design_comparator
- era_comparator
- tree_shadow_simulator
- vr_mingtang
- ray_tracer_worker
"""
import sys
import os
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PASS_COUNT = 0
FAIL_COUNT = 0


def record_result(name: str, passed: bool, detail: str = ""):
    global PASS_COUNT, FAIL_COUNT
    if passed:
        PASS_COUNT += 1
        logger.info(f"  ✅ PASS: {name}")
    else:
        FAIL_COUNT += 1
        logger.error(f"  ❌ FAIL: {name} — {detail}")


def _setup_path():
    base = os.path.join(os.path.dirname(__file__), '..', 'daylight_simulator')
    if base not in sys.path:
        sys.path.insert(0, base)
    backend_root = os.path.join(os.path.dirname(__file__), '..')
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)


# ============================================================
# Test 1: design_comparator 模块
# ============================================================

def test_design_comparator_list_dynasties():
    """UT-D1: list_dynasties 返回正确的朝代列表"""
    logger.info("=== Module Test: design_comparator — list_dynasties ===")
    try:
        _setup_path()
        from daylight_simulator.features.design_comparator import get_design_comparator

        cmp = get_design_comparator()
        dynasties = cmp.list_dynasties()

        assert isinstance(dynasties, list), "返回值应为list"
        assert len(dynasties) >= 3, "至少3个朝代"

        dynasty_keys = {d['key'] for d in dynasties}
        for expected in ['han', 'tang', 'ming']:
            assert expected in dynasty_keys, f"缺少朝代: {expected}"

        for d in dynasties:
            assert 'name' in d, f"{d['key']}缺少name"
            assert 'building_size' in d, f"{d['key']}缺少building_size"
            assert d['building_size']['length'] > 0, f"{d['key']}建筑长度应>0"
            assert 0 < d['window_transmittance'] <= 1, f"{d['key']}透光率应在(0,1]"

        record_result("UT-D1: list_dynasties 结构正确", True)
    except Exception as e:
        record_result("UT-D1: list_dynasties 结构正确", False, str(e))


def test_design_comparator_get_dynasty_summary():
    """UT-D2: get_dynasty_summary 获取单朝代设计概要"""
    logger.info("=== Module Test: design_comparator — get_dynasty_summary ===")
    try:
        _setup_path()
        from daylight_simulator.features.design_comparator import get_design_comparator

        cmp = get_design_comparator()

        han_summary = cmp.get_dynasty_summary('han')
        assert han_summary is not None, "汉朝概要不应为None"
        assert han_summary.dynasty == 'han'
        assert han_summary.building_specs['length'] > 0
        assert han_summary.building_specs['windows_count'] >= 4

        invalid_summary = cmp.get_dynasty_summary('invalid_dynasty')
        assert invalid_summary is not None, "无效朝代应回退到默认值"
        assert invalid_summary.dynasty == 'invalid_dynasty', "应保留输入的dynasty key"

        record_result("UT-D2: get_dynasty_summary 正确处理有效/无效朝代", True)
    except Exception as e:
        record_result("UT-D2: get_dynasty_summary 正确处理有效/无效朝代", False, str(e))


def test_design_comparator_rank_by_avg_illuminance():
    """UT-D3: rank_by_avg_illuminance 按照度降序排名"""
    logger.info("=== Module Test: design_comparator — rank_by_avg_illuminance ===")
    try:
        _setup_path()
        from daylight_simulator.features.design_comparator import DesignComparator
        from shared.schemas import DynastySimulationResult

        mock_results = [
            DynastySimulationResult(
                dynasty='han', dynasty_name='汉', year='西汉',
                avg_illuminance=30.0, min_illuminance=10.0, max_illuminance=50.0,
                uniformity=0.5, grid_size={'x': 5, 'y': 5, 'z': 3},
                illuminance_matrix=[], solar_altitude=60.0, solar_azimuth=180.0,
                building_specs={'length': 20, 'width': 20, 'height': 12, 'windows_count': 4, 'window_transmittance': 0.4}
            ),
            DynastySimulationResult(
                dynasty='tang', dynasty_name='唐', year='唐',
                avg_illuminance=50.0, min_illuminance=20.0, max_illuminance=80.0,
                uniformity=0.6, grid_size={'x': 5, 'y': 5, 'z': 3},
                illuminance_matrix=[], solar_altitude=60.0, solar_azimuth=180.0,
                building_specs={'length': 30, 'width': 30, 'height': 15, 'windows_count': 8, 'window_transmittance': 0.5}
            ),
            DynastySimulationResult(
                dynasty='ming', dynasty_name='明', year='明',
                avg_illuminance=40.0, min_illuminance=15.0, max_illuminance=65.0,
                uniformity=0.55, grid_size={'x': 5, 'y': 5, 'z': 3},
                illuminance_matrix=[], solar_altitude=60.0, solar_azimuth=180.0,
                building_specs={'length': 25, 'width': 25, 'height': 14, 'windows_count': 6, 'window_transmittance': 0.45}
            ),
        ]

        ranked = DesignComparator.rank_by_avg_illuminance(mock_results)

        assert ranked[0]['rank'] == 1
        assert ranked[0]['dynasty'] == 'tang', "照度最高的唐朝应排第一"
        assert ranked[1]['dynasty'] == 'ming'
        assert ranked[2]['dynasty'] == 'han'
        assert ranked[0]['avg_illuminance'] >= ranked[1]['avg_illuminance'] >= ranked[2]['avg_illuminance']

        record_result("UT-D3: rank_by_avg_illuminance 降序排名正确", True)
    except Exception as e:
        record_result("UT-D3: rank_by_avg_illuminance 降序排名正确", False, str(e))


def test_design_comparator_compare_illuminance():
    """UT-D4: compare_illuminance 多朝代照度对比仿真"""
    logger.info("=== Module Test: design_comparator — compare_illuminance ===")
    try:
        _setup_path()
        from daylight_simulator.features.design_comparator import get_design_comparator
        from shared.schemas import DynastyComparisonParams, DynastyType, SkyModelType

        cmp = get_design_comparator()

        params = DynastyComparisonParams(
            dynasties=[DynastyType.HAN, DynastyType.TANG, DynastyType.MING],
            date='2024-06-21',
            hour=12,
            sky_model=SkyModelType.PEREZ,
            turbidity=2.5,
            grid_resolution=5
        )

        progress_values = []

        def _progress(curr, tot):
            progress_values.append((curr, tot))

        results = cmp.compare_illuminance(params, progress_callback=_progress)

        assert isinstance(results, list), "返回值应为list"
        assert len(results) == 3, "应返回3个朝代的结果"

        for r in results:
            assert r.avg_illuminance > 0, f"{r.dynasty}平均照度应>0"
            assert 0 < r.uniformity <= 1, f"{r.dynasty}均匀度应在(0,1]"
            assert r.building_specs['length'] > 0

        assert len(progress_values) == 3, "进度回调应被调用3次"
        assert progress_values[-1] == (3, 3), "最后一次进度应为(3,3)"

        record_result("UT-D4: compare_illuminance 多朝代对比正确", True)
    except Exception as e:
        record_result("UT-D4: compare_illuminance 多朝代对比正确", False, str(e))


# ============================================================
# Test 2: era_comparator 模块
# ============================================================

def test_era_comparator_simulated_metrics_from_raw():
    """UT-E1: SimulatedMetrics.from_raw 采光系数计算正确"""
    logger.info("=== Module Test: era_comparator — SimulatedMetrics.from_raw ===")
    try:
        _setup_path()
        from daylight_simulator.features.era_comparator import SimulatedMetrics

        metrics = SimulatedMetrics.from_raw(
            avg_illuminance=500.0,
            min_illuminance=200.0,
            uniformity=0.65
        )

        expected_df_avg = (500.0 / 10000.0) * 100
        expected_df_min = (200.0 / 10000.0) * 100

        assert abs(metrics.daylight_factor_avg - expected_df_avg) < 0.01, \
            f"平均采光系数计算错误: {metrics.daylight_factor_avg} vs {expected_df_avg}"
        assert abs(metrics.daylight_factor_min - expected_df_min) < 0.01, \
            f"最低采光系数计算错误: {metrics.daylight_factor_min} vs {expected_df_min}"
        assert metrics.illuminance_avg == 500.0
        assert metrics.illuminance_min == 200.0
        assert metrics.uniformity_min == 0.65
        assert metrics.da300 > 0, "DA300应>0"
        assert metrics.udi_100_3000 > 0, "UDI应>0"

        zero_metrics = SimulatedMetrics.from_raw(0.0, 0.0, 0.0)
        assert zero_metrics.daylight_factor_avg == 0.0
        assert zero_metrics.da300 == 0.0
        assert zero_metrics.udi_100_3000 == 0.0

        record_result("UT-E1: SimulatedMetrics.from_raw 计算正确", True)
    except Exception as e:
        record_result("UT-E1: SimulatedMetrics.from_raw 计算正确", False, str(e))


def test_era_comparator_list_standards():
    """UT-E2: list_standards 列出所有标准（现代+古代）"""
    logger.info("=== Module Test: era_comparator — list_standards ===")
    try:
        _setup_path()
        from daylight_simulator.features.era_comparator import get_era_comparator

        cmp = get_era_comparator()
        standards = cmp.list_standards()

        assert isinstance(standards, list), "返回值应为list"
        assert len(standards) >= 4, "至少4项标准（3现代+1古代）"

        keys = {s['key'] for s in standards}
        assert 'gb50033_2013' in keys
        assert 'en17037_2019' in keys
        assert 'leed_v4_1' in keys
        assert 'ancient_ideal' in keys

        modern_count = sum(1 for s in standards if s['category'] != 'historical')
        ancient_count = sum(1 for s in standards if s['category'] == 'historical')
        assert modern_count >= 3
        assert ancient_count >= 1

        record_result("UT-E2: list_standards 包含现代和古代标准", True)
    except Exception as e:
        record_result("UT-E2: list_standards 包含现代和古代标准", False, str(e))


def test_era_comparator_compare():
    """UT-E3: compare 对比结果结构完整"""
    logger.info("=== Module Test: era_comparator — compare ===")
    try:
        _setup_path()
        from daylight_simulator.features.era_comparator import get_era_comparator

        cmp = get_era_comparator()
        results = cmp.compare(
            dynasty_key='tang',
            avg_illuminance=500.0,
            min_illuminance=200.0,
            uniformity=0.65
        )

        assert isinstance(results, list), "返回值应为list"
        assert len(results) >= 4, "至少对比4项标准"

        for r in results:
            assert 'standard_key' in r
            assert 'overall_score' in r
            assert 0 <= r['overall_score'] <= 1.5, "综合评分应在合理范围"
            assert 'simulated_metrics' in r
            assert 'standards_compliance' in r
            assert isinstance(r['standards_compliance'], dict)
            assert 'dynasty' in r
            assert r['dynasty'] == 'tang'

            for cat_key, comp in r['standards_compliance'].items():
                assert 'pass' in comp
                assert 'standard_value' in comp
                assert 'simulated_value' in comp

        record_result("UT-E3: compare 返回结构完整", True)
    except Exception as e:
        record_result("UT-E3: compare 返回结构完整", False, str(e))


def test_era_comparator_compliance_summary():
    """UT-E4: get_compliance_summary 合规性统计正确"""
    logger.info("=== Module Test: era_comparator — get_compliance_summary ===")
    try:
        _setup_path()
        from daylight_simulator.features.era_comparator import get_era_comparator

        cmp = get_era_comparator()
        results = cmp.compare('han', 500.0, 200.0, 0.65)
        summary = cmp.get_compliance_summary(results)

        assert 'modern_standards_count' in summary
        assert 'ancient_benchmarks_count' in summary
        assert 'avg_modern_score' in summary
        assert 'avg_ancient_score' in summary
        assert 'best_standard' in summary
        assert summary['modern_standards_count'] >= 3
        assert summary['ancient_benchmarks_count'] >= 1
        assert 0 <= summary['avg_modern_score'] <= 1

        empty_summary = cmp.get_compliance_summary([])
        assert empty_summary == {}, "空结果应返回空dict"

        record_result("UT-E4: get_compliance_summary 统计正确", True)
    except Exception as e:
        record_result("UT-E4: get_compliance_summary 统计正确", False, str(e))


# ============================================================
# Test 3: tree_shadow_simulator 模块
# ============================================================

def test_tree_shadow_simulator_list_species():
    """UT-T1: list_species 返回树种列表"""
    logger.info("=== Module Test: tree_shadow_simulator — list_species ===")
    try:
        _setup_path()
        from daylight_simulator.features.tree_shadow_simulator import get_tree_shadow_simulator

        sim = get_tree_shadow_simulator()
        species = sim.list_species()

        assert isinstance(species, list), "返回值应为list"
        assert len(species) >= 3, "至少3种树种"

        for sp in species:
            assert 'key' in sp
            assert 'name' in sp
            assert sp['canopy_radius'] > 0
            assert 0 <= sp['canopy_transmittance'] <= 1

        record_result("UT-T1: list_species 结构正确", True)
    except Exception as e:
        record_result("UT-T1: list_species 结构正确", False, str(e))


def test_tree_shadow_simulator_estimate_shadow_radius():
    """UT-T2: estimate_shadow_radius 阴影半径估算"""
    logger.info("=== Module Test: tree_shadow_simulator — estimate_shadow_radius ===")
    try:
        _setup_path()
        from daylight_simulator.features.tree_shadow_simulator import get_tree_shadow_simulator

        sim = get_tree_shadow_simulator()
        from daylight_simulator.features.tree_shadow_simulator import TreeInstance, TreeSpecies
        species = TreeSpecies(
            key='pine', name='古松',
            trunk_radius=0.5, trunk_height=4.0,
            canopy_radius=3.0, canopy_height=8.0,
            canopy_transmittance=0.3,
            albedo=[0.1, 0.3, 0.1],
            leaf_density=0.8
        )
        tree = TreeInstance(species_key='pine', position=[0, 0, 0], scale=1.0, species=species)

        r_high_sun = sim.estimate_shadow_radius(tree, 80.0)
        r_low_sun = sim.estimate_shadow_radius(tree, 30.0)

        assert r_low_sun > r_high_sun, "太阳高度角越低，阴影半径越大"
        assert r_high_sun > 0
        assert r_low_sun > 0

        r_high_noon = sim.estimate_shadow_radius(tree, 90.0)
        assert abs(r_high_noon - 3.0) < 0.1, "正午90度时阴影半径≈树冠半径"

        record_result("UT-T2: estimate_shadow_radius 符合物理规律", True)
    except Exception as e:
        record_result("UT-T2: estimate_shadow_radius 符合物理规律", False, str(e))


def test_tree_instance_effective_transmittance():
    """UT-T3: TreeInstance.effective_transmittance 季节透光率"""
    logger.info("=== Module Test: tree_shadow_simulator — effective_transmittance ===")
    try:
        _setup_path()
        from daylight_simulator.features.tree_shadow_simulator import TreeInstance, TreeSpecies

        species = TreeSpecies(
            key='ginkgo', name='银杏',
            trunk_radius=0.4, trunk_height=3.0,
            canopy_radius=4.0, canopy_height=6.0,
            canopy_transmittance=0.3,
            albedo=[0.3, 0.6, 0.2],
            leaf_density=0.9
        )

        tree = TreeInstance(
            species_key='ginkgo',
            position=[10, 10, 0],
            scale=1.0,
            season='summer',
            species=species
        )

        t_summer = tree.effective_transmittance(1.0)
        t_winter = tree.effective_transmittance(0.1)

        assert t_summer < t_winter, "夏季叶密透光率<冬季"
        assert 0 < t_summer <= 1
        assert 0 < t_winter <= 1

        no_species_tree = TreeInstance(species_key='unknown', position=[0, 0, 0])
        t_default = no_species_tree.effective_transmittance(0.5)
        assert abs(t_default - 0.35) < 0.01, "无树种时使用默认透光率0.35"

        record_result("UT-T3: effective_transmittance 季节差异正确", True)
    except Exception as e:
        record_result("UT-T3: effective_transmittance 季节差异正确", False, str(e))


def test_tree_shadow_simulator_simulate():
    """UT-T4: simulate 树木影响仿真"""
    logger.info("=== Module Test: tree_shadow_simulator — simulate ===")
    try:
        _setup_path()
        from daylight_simulator.features.tree_shadow_simulator import get_tree_shadow_simulator
        from shared.schemas import TreeImpactParams, DynastyType, TreeConfig

        sim = get_tree_shadow_simulator()

        params = TreeImpactParams(
            dynasty=DynastyType.HAN,
            date='2024-06-21',
            hour=12,
            trees=[
                TreeConfig(species='pine', position=[-8, 0, 0], scale=1.5),
                TreeConfig(species='ginkgo', position=[8, 0, 0], scale=1.5),
                TreeConfig(species='pine', position=[0, -8, 0], scale=1.5),
                TreeConfig(species='ginkgo', position=[0, 8, 0], scale=1.5),
            ],
            season='summer',
            grid_resolution=5
        )

        progress_values = []

        def _progress(p):
            progress_values.append(p)

        result = sim.simulate(params, progress_callback=_progress)

        assert result.without_trees['avg_illuminance'] > result.with_trees['avg_illuminance'], \
            "有树时平均照度应低于无树"
        assert result.illuminance_reduction_pct >= 0, "照度降幅应>=0"
        assert result.shaded_area_pct >= 0, "遮蔽面积应>=0"
        assert len(result.tree_details) == 4, "应返回4棵树的详情"

        assert len(progress_values) > 0, "进度回调应被调用"
        assert max(progress_values) <= 1.0, "进度不应超过1.0"

        record_result("UT-T4: simulate 树木影响仿真正确", True)
    except Exception as e:
        record_result("UT-T4: simulate 树木影响仿真正确", False, str(e))


# ============================================================
# Test 4: vr_mingtang 模块
# ============================================================

def test_vr_mingtang_interp_hour():
    """UT-V1: get_snapshot_at 小时插值正确"""
    logger.info("=== Module Test: vr_mingtang — get_snapshot_at ===")
    try:
        _setup_path()
        from daylight_simulator.features.vr_mingtang import get_vr_mingtang_tour
        from shared.schemas import VirtualTourParams, DynastyType

        tour = get_vr_mingtang_tour()

        params = VirtualTourParams(
            dynasty=DynastyType.HAN,
            date='2024-06-21',
            start_hour=10,
            end_hour=14,
            time_step=60,
            grid_resolution=5
        )

        result = tour.run_tour(params)

        snapshot_12 = tour.get_snapshot_at(result, 12.0)
        assert snapshot_12 is not None
        assert abs(snapshot_12.hour - 12.0) < 0.01

        snapshot_12_5 = tour.get_snapshot_at(result, 12.5)
        assert snapshot_12_5 is not None
        assert abs(snapshot_12_5.hour - 12.5) < 0.01
        assert snapshot_12_5.avg_illuminance > 0

        snapshot_out_of_range = tour.get_snapshot_at(result, 23.0)
        assert snapshot_out_of_range is not None, "超出范围应返回最近值"

        record_result("UT-V1: get_snapshot_at 插值正确", True)
    except Exception as e:
        record_result("UT-V1: get_snapshot_at 插值正确", False, str(e))


def test_vr_mingtang_sunrise_sunset():
    """UT-V2: find_sunrise_sunset 日出日落估算"""
    logger.info("=== Module Test: vr_mingtang — find_sunrise_sunset ===")
    try:
        _setup_path()
        from daylight_simulator.features.vr_mingtang import get_vr_mingtang_tour
        from shared.schemas import VirtualTourParams, VirtualTourResult, DynastyType

        tour = get_vr_mingtang_tour()

        params = VirtualTourParams(
            dynasty=DynastyType.HAN,
            date='2024-06-21',
            start_hour=4,
            end_hour=20,
            time_step=30,
            grid_resolution=5
        )

        result = tour.run_tour(params)
        sunrise, sunset = tour.find_sunrise_sunset(result)

        assert sunrise is not None
        assert sunset is not None
        assert 4 <= sunrise <= 8, "夏至日出应在4-8点"
        assert 17 <= sunset <= 21, "夏至日落应在17-21点"
        assert sunrise < sunset, "日出应早于日落"

        record_result("UT-V2: find_sunrise_sunset 估算合理", True)
    except Exception as e:
        record_result("UT-V2: find_sunrise_sunset 估算合理", False, str(e))


def test_vr_mingtang_run_tour():
    """UT-V3: run_tour 时序仿真"""
    logger.info("=== Module Test: vr_mingtang — run_tour ===")
    try:
        _setup_path()
        from daylight_simulator.features.vr_mingtang import get_vr_mingtang_tour
        from shared.schemas import VirtualTourParams, DynastyType

        tour = get_vr_mingtang_tour()

        params = VirtualTourParams(
            dynasty=DynastyType.TANG,
            date='2024-03-21',
            start_hour=8,
            end_hour=16,
            time_step=60,
            grid_resolution=5
        )

        progress_values = []

        def _progress(p):
            progress_values.append(p)

        result = tour.run_tour(params, progress_callback=_progress)

        assert result.dynasty == 'tang'
        assert len(result.hourly_data) >= 8, "8-16点步长60分钟应至少9个点"
        assert len(result.sun_path) == len(result.hourly_data), "太阳轨迹点数应与时序数据一致"

        illuminances = [d.avg_illuminance for d in result.hourly_data]
        max_idx = illuminances.index(max(illuminances))
        assert 11 <= result.hourly_data[max_idx].hour <= 13, "照度峰值应在午间"

        for d in result.hourly_data:
            assert d.solar_altitude >= -90
            assert 0 <= d.solar_azimuth <= 360

        assert len(progress_values) > 0
        assert max(progress_values) <= 1.0

        record_result("UT-V3: run_tour 时序仿真正确", True)
    except Exception as e:
        record_result("UT-V3: run_tour 时序仿真正确", False, str(e))


def test_vr_mingtang_azimuth_interpolation():
    """UT-V4: _interp_azimuth 方位角插值处理0°/360°跨越"""
    logger.info("=== Module Test: vr_mingtang — _interp_azimuth ===")
    try:
        _setup_path()
        from daylight_simulator.features.vr_mingtang import VRMingtangTour

        tour = VRMingtangTour()

        az_350 = tour._interp_azimuth(350.0, 10.0, 0.5)
        assert abs(az_350 - 0.0) < 1.0, "350°→10° 中点应为0°"

        az_10 = tour._interp_azimuth(10.0, 350.0, 0.5)
        assert abs(az_10 - 0.0) < 1.0, "10°→350° 中点应为0°"

        az_normal = tour._interp_azimuth(90.0, 180.0, 0.5)
        assert abs(az_normal - 135.0) < 0.1, "正常线性插值"

        record_result("UT-V4: _interp_azimuth 跨0°处理正确", True)
    except Exception as e:
        record_result("UT-V4: _interp_azimuth 跨0°处理正确", False, str(e))


# ============================================================
# Test 5: ray_tracer_worker 模块（基础功能，不启动进程）
# ============================================================

def test_worker_dataclasses():
    """UT-W1: Worker任务/结果 dataclass 结构正确"""
    logger.info("=== Module Test: ray_tracer_worker — dataclasses ===")
    try:
        _setup_path()
        from daylight_simulator.workers.ray_tracer_worker import (
            WorkerTask, WorkerTaskType, WorkerResult, WorkerTaskStatus
        )

        task = WorkerTask(
            task_id='test_123',
            task_type=WorkerTaskType.ILLUMINANCE_SINGLE,
            payload={'dynasty': 'han', 'date': '2024-06-21'}
        )

        assert task.task_id == 'test_123'
        assert task.task_type == WorkerTaskType.ILLUMINANCE_SINGLE
        assert task.payload['dynasty'] == 'han'
        assert task.status == WorkerTaskStatus.PENDING

        result = WorkerResult(
            task_id='test_123',
            status=WorkerTaskStatus.COMPLETED,
            result={'avg_illuminance': 100.0},
            progress=1.0
        )

        assert result.status == WorkerTaskStatus.COMPLETED
        assert result.result['avg_illuminance'] == 100.0

        record_result("UT-W1: Worker dataclass 结构正确", True)
    except Exception as e:
        record_result("UT-W1: Worker dataclass 结构正确", False, str(e))


def test_worker_manager_lifecycle():
    """UT-W2: RayTracerWorkerManager 生命周期（不启动子进程）"""
    logger.info("=== Module Test: ray_tracer_worker — manager lifecycle ===")
    try:
        _setup_path()
        from daylight_simulator.workers.ray_tracer_worker import RayTracerWorkerManager

        mgr = RayTracerWorkerManager(num_workers=0)

        assert mgr.num_workers == 0
        assert not mgr._running

        mgr.start()
        assert mgr._running

        mgr.stop()
        assert not mgr._running

        record_result("UT-W2: WorkerManager 生命周期正常", True)
    except Exception as e:
        record_result("UT-W2: WorkerManager 生命周期正常", False, str(e))


# ============================================================
# 运行所有测试
# ============================================================

def run_all():
    logger.info("=" * 60)
    logger.info("新模块单元测试 — 4个功能模块 + Worker进程")
    logger.info("覆盖: design_comparator | era_comparator | tree_shadow_simulator | vr_mingtang | ray_tracer_worker")
    logger.info("=" * 60)

    # design_comparator
    test_design_comparator_list_dynasties()
    test_design_comparator_get_dynasty_summary()
    test_design_comparator_rank_by_avg_illuminance()
    test_design_comparator_compare_illuminance()

    # era_comparator
    test_era_comparator_simulated_metrics_from_raw()
    test_era_comparator_list_standards()
    test_era_comparator_compare()
    test_era_comparator_compliance_summary()

    # tree_shadow_simulator
    test_tree_shadow_simulator_list_species()
    test_tree_shadow_simulator_estimate_shadow_radius()
    test_tree_instance_effective_transmittance()
    test_tree_shadow_simulator_simulate()

    # vr_mingtang
    test_vr_mingtang_interp_hour()
    test_vr_mingtang_sunrise_sunset()
    test_vr_mingtang_run_tour()
    test_vr_mingtang_azimuth_interpolation()

    # ray_tracer_worker
    test_worker_dataclasses()
    test_worker_manager_lifecycle()

    logger.info("=" * 60)
    total = PASS_COUNT + FAIL_COUNT
    pass_rate = PASS_COUNT / total * 100 if total > 0 else 0
    logger.info(f"单元测试结果: ✅ {PASS_COUNT} 通过 | ❌ {FAIL_COUNT} 失败")
    logger.info(f"通过率: {pass_rate:.1f}%")
    logger.info("=" * 60)

    if FAIL_COUNT > 0:
        logger.error("存在单元测试失败！")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(run_all())
