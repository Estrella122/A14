from __future__ import annotations

import importlib.util
from pathlib import Path

_IMPLEMENTATION = Path(__file__).with_name("industrial-analysis") / "executor.py"
_SPEC = importlib.util.spec_from_file_location("a14_industrial_analysis_executor", _IMPLEMENTATION)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"无法加载 industrial-analysis executor：{_IMPLEMENTATION}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

execute_analysis = _MODULE.execute_analysis
execute_capability = _MODULE.execute_capability

__all__ = ["execute_analysis", "execute_capability"]
