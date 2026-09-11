"""Read-only bridge for the four member delivery packages.

The packages are kept under ``integrations/`` unchanged.  This adapter exposes
their published evidence in the main Django service, so the Vue application has
one origin and does not depend on four separately started web servers.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


INTEGRATIONS_ROOT = Path(settings.BASE_DIR) / "integrations"


def _read_json(relative_path: str, default=None):
    path = INTEGRATIONS_ROOT / relative_path
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(relative_path: str, limit: int = 12):
    path = INTEGRATIONS_ROOT / relative_path
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))[:limit]


def _response(payload, status=200):
    response = JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})
    response["Access-Control-Allow-Origin"] = "*"
    return response


def standardization_payload():
    report = _read_json("standardization/outputs/A14_task2/task2_acceptance_report.json")
    implementation = INTEGRATIONS_ROOT / "standardization/standard_agent/engine.py"
    return {
        "module": "统一标准与多场景模板（2号）",
        "source": "2号原始交付物 · task2_acceptance_report.json",
        "available": implementation.exists(),
        "evidence_available": bool(report),
        "passed": report.get("passed", False),
        "passed_items": report.get("passed_items", 0),
        "total_items": report.get("total_items", 0),
        "generated_at": report.get("generated_at"),
        "checks": report.get("items", [])[:8],
        "template_count": 3,
        "mapping_preview": _read_csv("standardization/standards/scenarios/blast_furnace/fields.csv", 8),
    }


def cleaning_payload():
    report = _read_json("data_cleaning/output/output（5）/quality_report.json")
    implementation = INTEGRATIONS_ROOT / "data_cleaning/src/data_cleaning_agent.py"
    return {
        "module": "数据清洗与优质数据筛选（3号）",
        "source": "3号原始交付物 · quality_report.json",
        "available": implementation.exists(),
        "evidence_available": bool(report),
        "overall_score": report.get("overall_score"),
        "dimension_scores": report.get("dimension_scores", {}),
        "missing_rate": report.get("missing_rate", {}),
        "selected_segment_count": report.get("selected_segment_count", 0),
        "logs": report.get("logs", []),
        "segments": _read_csv("data_cleaning/output/output（5）/selected_dynamic_segments.csv", 8),
    }


def modeling_payload():
    summary = _read_json("identification/outputs/modeling_pipeline_demo/pipeline_summary.json")
    metrics = _read_json("identification/outputs/modeling_pipeline_demo/03_system_identification/model_metrics.json")
    recommendation = _read_json("identification/outputs/modeling_pipeline_demo/02_collinearity/variable_recommendation.json")
    implementation = INTEGRATIONS_ROOT / "identification/system_identification.py"
    if not implementation.exists():
        implementation = next((path for path in (INTEGRATIONS_ROOT / "identification").glob("*.py")), implementation)
    return {
        "module": "时滞分析与系统辨识（4号）",
        "source": "4号原始交付物 · modeling_pipeline_demo",
        "available": implementation.exists(),
        "evidence_available": bool(summary),
        "input_columns": summary.get("input_cols", []),
        "selected_inputs": summary.get("selected_inputs_after_collinearity", []),
        "config": summary.get("config", {}),
        "metrics": metrics,
        "recommendation": recommendation,
        "lags": _read_csv("identification/outputs/modeling_pipeline_demo/01_time_delay/delay_estimates.csv", 8),
    }


def agent_payload():
    candidate = _read_json("agent_control/runtime/artifacts/run_a1f3a6251227/candidate_002_evaluation.json")
    model = _read_json("agent_control/runtime/artifacts/run_a1f3a6251227/model_iter_1.json")
    return {
        "module": "Agent 总控编排（1号）",
        "source": "1号原始交付物 · run_a1f3a6251227",
        "available": bool(candidate),
        "candidate": candidate,
        "model": model,
        "stages": ["字段标准化", "数据清洗", "动态筛选", "时滞分析", "共线性处理", "ARX 辨识", "评审决策"],
    }


PAYLOAD_BUILDERS = {
    "standardization": standardization_payload,
    "cleaning": cleaning_payload,
    "modeling": modeling_payload,
    "agent": agent_payload,
}


@require_GET
def integration_module(request, module_key):
    builder = PAYLOAD_BUILDERS.get(module_key)
    if not builder:
        return _response({"ok": False, "message": "未知集成模块"}, status=404)
    return _response({"ok": True, "data": builder()})


@require_GET
def integration_summary(request):
    modules = {key: builder() for key, builder in PAYLOAD_BUILDERS.items()}
    return _response({
        "ok": True,
        "integration_mode": "主工程统一服务 · 原始交付物只读接入",
        "modules": modules,
    })
