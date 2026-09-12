from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd


def _result(skill_id: str, started: float, *, status: str = "success", capabilities: list[str] | None = None,
            facts: list[str] | None = None, findings: list[str] | None = None, hypotheses: list[str] | None = None,
            limitations: list[str] | None = None, metrics: dict[str, Any] | None = None, artifacts: list[str] | None = None,
            evidence: list[Any] | None = None, warnings: list[str] | None = None, trace: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "status": status, "skill_id": skill_id, "capabilities_executed": capabilities or [],
        "facts": facts or [], "findings": findings or [], "hypotheses": hypotheses or [],
        "limitations": limitations or [], "metrics": metrics or {}, "artifacts": artifacts or [],
        "evidence": evidence or [], "warnings": warnings or [], "execution_trace": trace or [],
        "duration_ms": round((perf_counter() - started) * 1000),
    }


def _artifact_path(snapshot: dict[str, Any], key: str) -> Path | None:
    run_id = snapshot.get("run_id")
    if not run_id or key not in snapshot.get("artifacts", {}):
        return None
    try:
        from core.services.pipeline import resolve_artifact
        return resolve_artifact(str(run_id), key)[0]
    except Exception:
        return None


class StandardizationExecutor:
    skill_id = "standardization"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.pipeline import run_standardization_stage
        started = perf_counter()
        snapshot, state = inputs["snapshot"], runtime_context["state"]
        source = inputs.get("data_path") or _artifact_path(snapshot, "source_csv")
        if source is None and snapshot.get("_dataframe") is not None:
            source = Path(runtime_context["output_dir"]) / "input" / "source.csv"
            source.parent.mkdir(parents=True, exist_ok=True)
            snapshot["_dataframe"].to_csv(source, index=False)
        if source is None:
            return _result(skill_id, started, status="blocked", limitations=["缺少源 CSV 或 DataFrame 文件引用。"])
        run_dir = Path(runtime_context["output_dir"]) / "standardization"
        frame, report = run_standardization_stage(Path(source), run_dir, "auto", task_spec.get("objective", ""), inputs.get("overrides"))
        state.update(standardized_data=frame, standardization=report, dictionary=report.get("dictionary", []), stage_run_dir=run_dir)
        mapping = report.get("mapping", {})
        return _result(skill_id, started, capabilities=capability_ids,
            facts=[f"自动识别数据场景为 {report.get('scenario', {}).get('scenario_id', 'unknown')}。",
                   f"字段覆盖 {mapping.get('matched_count', 0)}/{report.get('source_column_count', len(frame.columns))}。"],
            limitations=[item.get("message", str(item)) for item in report.get("issues", [])],
            metrics={"scene": report.get("scenario", {}), "mapping": mapping, "data_decision": report.get("data_decision", {})},
            artifacts=list(report.get("artifacts", {}).values()), evidence=[report.get("runtime_trace", {})],
            trace=[{"step": "StandardizationAgent.standardize", "scenario_id": "auto", "status": "completed"}])


class CleaningExecutor:
    skill_id = "cleaning"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.pipeline import run_cleaning_stage, _read_csv
        started = perf_counter()
        snapshot, state = inputs["snapshot"], runtime_context["state"]
        standardized = state.get("standardized_data")
        if standardized is None:
            path = _artifact_path(snapshot, "standardized_csv")
            standardized = _read_csv(path) if path else None
        standard = state.get("standardization") or snapshot.get("results", {}).get("standardization", {})
        dictionary = state.get("dictionary") or standard.get("dictionary", [])
        if standardized is None or not dictionary:
            return _result(skill_id, started, status="blocked", limitations=["缺少标准化数据或字段字典。"])
        run_dir = Path(runtime_context["output_dir"]) / "cleaning"
        params = inputs.get("parameters", {})
        modeling, segments, report = run_cleaning_stage(
            standardized, dictionary, run_dir, params.get("resample_rule", "10s"), params.get("max_lag", 60),
            primary_output=standard.get("scenario", {}).get("primary_output"),
            selection_window=standard.get("scenario", {}).get("selection_window_samples", 30),
            selection_step=standard.get("scenario", {}).get("selection_step_samples", 15),
            include_segmentation="segmentation" in runtime_context.get("target_groups", []),
        )
        state.update(modeling_data=modeling, segments=segments, cleaning=report, dictionary=dictionary, stage_run_dir=run_dir)
        before = int(report.get("source_row_count") or len(standardized))
        after = int(report.get("cleaned_row_count") or 0)
        audit = {"rows_before": before, "rows_after": after, "rows_changed": abs(before - after),
                 "rules": report.get("logs", []), "missing_rate": report.get("missing_rate", {}),
                 "anomaly_rate": report.get("anomaly_rate", {})}
        return _result(skill_id, started, capabilities=capability_ids,
            facts=[f"清洗前 {before} 行，清洗后 {after} 行。"],
            findings=[f"质量评分 {report.get('overall_score', 'unknown')}；候选动态段 {report.get('selected_segment_count', 0)} 个。"],
            limitations=["窗口 SNR 是代理估计，不能视为仪表标定结果。"], metrics=audit,
            artifacts=list(report.get("artifacts", {}).values()), evidence=[audit],
            trace=[{"step": "DataCleaningSelectionAgent", "status": "completed", "rules": report.get("logs", [])}])


class ModelingExecutor:
    skill_id = "modeling"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.pipeline import run_modeling_stage, _read_csv
        started = perf_counter()
        snapshot, state = inputs["snapshot"], runtime_context["state"]
        modeling = state.get("modeling_data")
        if modeling is None:
            path = _artifact_path(snapshot, "modeling_csv")
            modeling = _read_csv(path) if path else None
        standard = state.get("standardization") or snapshot.get("results", {}).get("standardization", {})
        dictionary = state.get("dictionary") or standard.get("dictionary", [])
        if modeling is None or not dictionary:
            return _result(skill_id, started, status="blocked", limitations=["缺少建模数据或字段字典。"])
        run_dir = Path(runtime_context["output_dir"]) / "modeling"
        run_dir.mkdir(parents=True, exist_ok=True)
        # _model expects the frozen split artifacts beside its run directory. Copying is avoided;
        # a prior executor supplies its own stage directory, otherwise use the pipeline run directory.
        source_run_dir = state.get("stage_run_dir")
        if source_run_dir and (Path(source_run_dir) / "03_cleaning").exists():
            run_dir = Path(source_run_dir)
        elif snapshot.get("run_id"):
            from core.services.pipeline import RUNS_DIR
            run_dir = RUNS_DIR / str(snapshot["run_id"])
        params = inputs.get("parameters", {})
        report = run_modeling_stage(modeling, dictionary, run_dir, params.get("max_lag", 60),
                        primary_output=standard.get("scenario", {}).get("primary_output"))
        state["modeling"] = report
        diagnostics = report.get("diagnostics", {}).get("test", {})
        baseline = {
            "persistence": diagnostics.get("persistence"),
            "rmse_improvement_over_persistence_pct": diagnostics.get("rmse_improvement_over_persistence_pct"),
            "multi_step_persistence": diagnostics.get("multi_step", {}).get("persistence"),
        }
        return _result(skill_id, started, capabilities=capability_ids,
            facts=[f"模型族 {report.get('config', {}).get('family', 'unknown')}，训练样本 {report.get('training_rows', 0)}。"],
            findings=[f"独立测试相对持续值基线 RMSE 改善 {baseline['rmse_improvement_over_persistence_pct']}%。"],
            limitations=["模型结论仅适用于冻结的数据分区和已记录输入范围。"],
            metrics={"model": report.get("config", {}), "train": report.get("metrics", {}).get("train", {}),
                     "validation": report.get("metrics", {}).get("validation", {}), "test": report.get("metrics", {}).get("test", {}),
                     "baseline_comparison": baseline}, artifacts=list(report.get("artifacts", {}).values()),
            evidence=[report.get("order_search", []), report.get("diagnostics", {})],
            trace=[{"step": "run_validated_modeling", "status": "completed", "baseline_compared": True}])


class OptimizationExecutor:
    skill_id = "optimization"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        started = perf_counter()
        required = {"objective", "model", "bounds", "constraints", "real_data"}
        request = inputs.get("optimization_request") or {}
        missing = sorted(required - {key for key, value in request.items() if value not in (None, "", [], {})})
        if missing:
            return _result(skill_id, started, status="blocked", limitations=["优化缺少前置条件：" + "、".join(missing)],
                           warnings=["没有生成或回退到 synthetic data。"], evidence=[{"synthetic_fallback": False, "missing": missing}])
        return _result(skill_id, started, status="partial", limitations=["独立优化执行器尚未完成迁移；现有 Pipeline 仍保留真实数据候选搜索。"],
                       warnings=["skill_runtime 模式不使用 Pipeline fallback。"])


class ReviewExecutor:
    skill_id = "review"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.pipeline import run_review_stage
        started = perf_counter()
        snapshot, state = inputs["snapshot"], runtime_context["state"]
        results = snapshot.get("results", {})
        standard = state.get("standardization") or results.get("standardization")
        cleaning = state.get("cleaning") or results.get("cleaning")
        modeling = state.get("modeling") or results.get("modeling")
        if not all((standard, cleaning, modeling)):
            return _result(skill_id, started, status="blocked", limitations=["缺少标准化、清洗或建模证据；评审没有触发重算。"])
        output = Path(runtime_context["output_dir"]) / "review"
        report = run_review_stage(standard, cleaning, modeling, output)
        state["review"] = report
        return _result(skill_id, started, capabilities=capability_ids, findings=[report["conclusion"]],
                       limitations=list(report.get("blockers", [])), metrics={"passed": report.get("passed"), "deployment_readiness": report.get("deployment_readiness")},
                       artifacts=[str(output / "06_review" / "agent_review.json")], evidence=[report.get("evidence", {})], warnings=report.get("warnings", []),
                       trace=[{"step": "review_existing_evidence", "recomputed": False, "status": "completed"}])


class ReportExecutor:
    skill_id = "report"

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        from core.services.report_service import render_execution_report
        started = perf_counter()
        try:
            report = render_execution_report(inputs["snapshot"], runtime_context.get("results", []), Path(runtime_context["output_dir"]) / "report")
        except ValueError as exc:
            return _result(skill_id, started, status="blocked", limitations=[str(exc)])
        return _result(skill_id, started, capabilities=capability_ids, facts=["报告仅格式化既有结果，没有重跑 Pipeline。"],
                       metrics={"title": report["title"], "sections": report["sections"]}, artifacts=[report["path"]],
                       evidence=[{"source_run": inputs["snapshot"].get("run_id"), "recomputed": False}],
                       trace=[{"step": "render_existing_results", "recomputed": False, "status": "completed"}])
