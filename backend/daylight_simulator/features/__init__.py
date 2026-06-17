#!/usr/bin/env python3
"""
features 包 — 4个独立功能模块
- design_comparator: 不同朝代明堂采光设计对比
- era_comparator: 古代与现代采光标准跨时代对比
- tree_shadow_simulator: 庭院树木对采光影响仿真
- vr_mingtang: 虚拟参观明堂体验
"""
from .design_comparator import DesignComparator, get_design_comparator
from .era_comparator import EraComparator, get_era_comparator
from .tree_shadow_simulator import TreeShadowSimulator, get_tree_shadow_simulator
from .vr_mingtang import VRMingtangTour, get_vr_mingtang_tour

__all__ = [
    "DesignComparator", "get_design_comparator",
    "EraComparator", "get_era_comparator",
    "TreeShadowSimulator", "get_tree_shadow_simulator",
    "VRMingtangTour", "get_vr_mingtang_tour",
]
