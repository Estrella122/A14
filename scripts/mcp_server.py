#!/usr/bin/env python
"""Portable entry point for MCP hosts that do not support a working-directory option."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.mcp.server import main


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
