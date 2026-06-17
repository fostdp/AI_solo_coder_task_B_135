#!/usr/bin/env python3
"""重构完成最终验证脚本"""
import sys
import os
sys.path.insert(0, '.')

print("=" * 70)
print("明堂采光仿真系统 — 重构完成验证")
print("=" * 70)

# 1. 后端模块结构验证
print("\n📦 后端模块结构验证:")
modules = [
    ("design_comparator", "daylight_simulator/features/design_comparator/__init__.py"),
    ("era_comparator", "daylight_simulator/features/era_comparator/__init__.py"),
    ("tree_shadow_simulator", "daylight_simulator/features/tree_shadow_simulator/__init__.py"),
    ("vr_mingtang", "daylight_simulator/features/vr_mingtang/__init__.py"),
    ("ray_tracer_worker", "daylight_simulator/workers/ray_tracer_worker.py"),
]

all_modules_ok = True
for name, path in modules:
    full_path = os.path.join(os.path.dirname(__file__), path)
    exists = os.path.exists(full_path)
    status = "✅" if exists else "❌"
    print(f"  {status} {name:<25} -> {path}")
    if not exists:
        all_modules_ok = False

# 2. 前端组件结构验证
print("\n🎨 前端组件结构验证:")
frontend_base = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'modules', 'daylight_panel')
components = [
    ("DynastyComparisonPanel", "components/dynasty_comparator/index.tsx"),
    ("StandardsComparisonPanel", "components/era_comparator/index.tsx"),
    ("TreeImpactPanel", "components/tree_shadow_simulator/index.tsx"),
    ("VirtualTourPanel", "components/vr_mingtang/index.tsx"),
]

all_components_ok = True
for name, path in components:
    full_path = os.path.join(frontend_base, path)
    exists = os.path.exists(full_path)
    status = "✅" if exists else "❌"
    print(f"  {status} {name:<25} -> {path}")
    if not exists:
        all_components_ok = False

# 3. 模块导入验证
print("\n🔗 模块导入验证:")
try:
    from daylight_simulator.features import (
        DesignComparator, EraComparator,
        TreeShadowSimulator, VRMingtangTour,
        get_design_comparator, get_era_comparator,
        get_tree_shadow_simulator, get_vr_mingtang_tour
    )
    from daylight_simulator.workers import RayTracerWorkerManager
    print("  ✅ 所有模块导入成功")
    imports_ok = True
except ImportError as e:
    print(f"  ❌ 导入失败: {e}")
    imports_ok = False

# 4. 运行测试
print("\n🧪 测试结果:")
from scripts.features_test import FeaturesTestSuite as FTS, PASS_COUNT as F_PASS, FAIL_COUNT as F_FAIL
from scripts.modules_unit_test import run_all as run_unit, PASS_COUNT as U_PASS, FAIL_COUNT as U_FAIL

print("  运行原有功能测试...")
fts = FTS()
f_result = fts.run_all()
print(f"  原有功能测试: ✅ {F_PASS} 通过 | ❌ {F_FAIL} 失败")

print("\n  运行新模块单元测试...")
u_result = run_unit()
print(f"  新模块单元测试: ✅ {U_PASS} 通过 | ❌ {U_FAIL} 失败")

# 5. 汇总
print("\n" + "=" * 70)
print("📊 重构完成汇总:")
print(f"  后端独立模块:  {len(modules)} 个 {'✅' if all_modules_ok else '❌'}")
print(f"  前端独立组件:  {len(components)} 个 {'✅' if all_components_ok else '❌'}")
print(f"  模块导入验证:  {'✅ 通过' if imports_ok else '❌ 失败'}")
print(f"  原有测试:      ✅ {F_PASS} 通过 | ❌ {F_FAIL} 失败 ({'无回归' if F_FAIL == 0 else '有回归'})")
print(f"  单元测试:      ✅ {U_PASS} 通过 | ❌ {U_FAIL} 失败")
print("=" * 70)

total_ok = all_modules_ok and all_components_ok and imports_ok and (F_FAIL == 0) and (U_FAIL == 0)
print(f"\n🎯 重构验证 {'通过 ✅' if total_ok else '失败 ❌'}")

sys.exit(0 if total_ok else 1)
