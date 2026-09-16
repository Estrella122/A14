#!/usr/bin/env python
"""Exit successfully only when the configured MCP server exposes the expected tools."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.mcp.client import check_server


def check(url: str) -> None:
    result = check_server(url)
    if not result.get("online"):
        missing = result.get("missing_tools") or ["required modeling tools"]
        raise RuntimeError("MCP 不可用或缺少工具：" + "、".join(missing))


if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010/mcp")
