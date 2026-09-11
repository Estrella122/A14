"""Compatibility adapter for the project-local, standalone industrial-analysis Skill."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_IMPLEMENTATION = Path(__file__).with_name("industrial-analysis") / "scripts" / "build_analysis_plan.py"
_SPEC = importlib.util.spec_from_file_location("a14_industrial_analysis", _IMPLEMENTATION)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"无法加载 industrial-analysis：{_IMPLEMENTATION}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

CAPABILITIES = _MODULE.CAPABILITIES
GENERIC_UNKNOWN_SAFE = _MODULE.GENERIC_UNKNOWN_SAFE
build_analysis_plan = _MODULE.build_analysis_plan

__all__ = ["CAPABILITIES", "GENERIC_UNKNOWN_SAFE", "build_analysis_plan"]
