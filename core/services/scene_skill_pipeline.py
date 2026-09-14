"""Scenario-neutral ingestion adapter into the existing Markdown Skill Runtime."""
from pathlib import Path
from time import perf_counter
from uuid import uuid4
import shutil
from hashlib import sha256
from django.conf import settings
from core.skills.artifacts import RuntimeArtifactResolver, LEGACY_ARTIFACT_TYPES
from core.skills.context import build_scene_context
from core.skills.runtime import execute_skill_plan, plan_skills


def run_scene_skill_pipeline(source, message="分析当前场景的数据质量并判断是否适合 ARX 建模。", *, output_root=None):
    from .pipeline import run_standardization_stage, _write_json
    tick = perf_counter()
    source = Path(source).resolve()
    run_id = "scene_" + uuid4().hex[:12]
    directory = Path(output_root or Path(settings.PROCESSPILOT_RUNTIME_ROOT)/"agent_skill_runs"/"scene_inputs")/run_id
    directory.mkdir(parents=True,exist_ok=True)
    stored = directory/"source.csv"; shutil.copy2(source,stored)
    _, standard = run_standardization_stage(stored,directory,"auto","")
    snapshot = {"run_id":run_id,"dataset_ref":str(source),"original_name":source.name,"status":"completed","results":{"standardization":standard},"runtime_trace":standard.get("runtime_trace",{}),"artifacts":{}}
    resolver = RuntimeArtifactResolver(snapshot)
    refs = [resolver.register("SOURCE_DATA",stored,"ingestion",run_id).public()]
    for key,relative in standard["artifacts"].items():
        if key in LEGACY_ARTIFACT_TYPES:
            refs.append(resolver.register(LEGACY_ARTIFACT_TYPES[key],directory/relative,"standardization",run_id).public())
    snapshot["artifact_registry"] = refs
    context = build_scene_context(snapshot).public()
    plan = plan_skills(message,run_id,snapshot=snapshot)
    decision = standard.get("data_decision",{})
    blocked = "字段/单位标准化拒绝：" + "；".join(decision.get("reasons",[])) if decision.get("status") == "reject" else None
    if standard.get("mapping",{}).get("missing_required"):
        blocked = "缺少必须的标准字段：" + ", ".join(standard["mapping"]["missing_required"])
    result = execute_skill_plan(plan,snapshot,blocked_reason=blocked)
    receipt = {"scenario_id":context["scenario_id"],"dataset_ref":str(source),"run_id":run_id,
        "skill_run_id":result["skill_run_id"],"scene_context":context,"skill_plan":plan,
        "skill_ids":[row["skill_id"] for row in plan["steps"]],
        "manifest_paths":[row.get("audit",{}).get("manifest_path") for row in result["executions"]],
        "executor_modules":[row.get("audit",{}).get("executor_module") for row in result["executions"]],
        "parameters":{row["skill_id"]:row.get("audit",{}).get("parameter_snapshot",{}) for row in result["executions"]},
        "status":"unavailable" if blocked else "success" if result["status"] == "completed" else result["status"],
        "runtime_status":result["status"], "unavailable_reason":blocked,
        "dataset_sha256":sha256(source.read_bytes()).hexdigest(), "metrics":{row["skill_id"]:row["metrics"] for row in result["executions"]},
        "warnings":{row["skill_id"]:row["warnings"] for row in result["executions"]},
        "artifacts":result["artifact_registry"],"executions":result["executions"],
        "standardization":{"scene":standard["scenario"],"mapping":standard["mapping"],"data_decision":decision},
        "elapsed_ms":round((perf_counter()-tick)*1000,3)}
    _write_json(directory/"snapshot.json",snapshot)
    _write_json(directory/"acceptance.json",receipt)
    return receipt
