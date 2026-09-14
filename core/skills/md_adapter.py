"""Bridge MD executors to the existing SkillResult and artifact/audit runtime."""
from datetime import datetime
from importlib import import_module
from pathlib import Path
from time import perf_counter
import math

from .artifacts import RuntimeArtifactResolver
from .contracts import execution_state_for


def json_value(value):
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if hasattr(value, "item"):
        return json_value(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def output(context, metrics, evidence, *, artifacts=None, status="success", warnings=None, algorithm=None):
    metrics, evidence = json_value(metrics), json_value(evidence)
    refs = artifacts or []
    return {"status": status, "metrics": metrics, "artifacts": refs, "evidence": evidence,
            "warnings": warnings or [], "suggested_next_skills": [],
            "execution_trace": [{"step": algorithm, "status": "completed"}] if algorithm else [],
            "algorithm_invoked": bool(algorithm)}


def persist(context, artifact_type, payload, filename):
    return context["resolver"].write_json(artifact_type, json_value(payload),
        Path(context["output_dir"]) / filename, context["skill_id"], context["execution_id"]).public()


def effective_parameters(manifest, scene, explicit=None):
    parameters = {p["name"]: p["default"] for p in manifest.metadata.get("parameters", []) if "default" in p}
    parameters.update(scene.get("default_parameters", {}))
    parameters.update(scene.get("metadata", {}).get("skill_overrides", {}).get(manifest.id, {}))
    parameters.update(explicit or {})
    return parameters


class MarkdownExecutor:
    def __init__(self, manifest):
        self.manifest = manifest

    def execute(self, skill_id, capability_ids, task_spec, data_context, inputs, runtime_context):
        manifest = self.manifest
        started = datetime.now().astimezone().isoformat()
        tick = perf_counter()
        resolver = RuntimeArtifactResolver(inputs["snapshot"], runtime_context["state"])
        input_refs = []
        for required in manifest.requires:
            ref = resolver.resolve(required)
            input_refs.append(ref.public() if ref else {"artifact_type": required, "source": "snapshot"})
        scene = data_context.get("scene_context", {})
        parameters = effective_parameters(manifest, scene, inputs.get("parameters"))
        context = {**runtime_context, "skill_id": manifest.id, "resolver": resolver,
                   "task_spec": task_spec, "data_context": data_context, "scene_context": scene,
                   "output_dir": Path(runtime_context["output_dir"]) / manifest.id}
        invoked = False
        try:
            for declaration in manifest.metadata.get("parameters", []):
                key = declaration["name"]
                if declaration.get("required") and key not in parameters:
                    raise ValueError(f"missing parameter: {key}")
                expected = {"float": (int, float), "integer": (int,), "list": (list,), "string": (str,), "boolean": (bool,)}[declaration["type"]]
                if key in parameters and (not isinstance(parameters[key], expected) or isinstance(parameters[key], bool) and declaration["type"] != "boolean"):
                    raise ValueError(f"invalid parameter: {key}")
            function = getattr(import_module(manifest.executor["module"]), manifest.executor["function"])
            if manifest.execution_mode == "unavailable":
                result = output(context, {}, [], status="unavailable", warnings=["Manifest 标记能力不可用"])
            else:
                invoked = True
                result = function(context, inputs, parameters)
            if not isinstance(result, dict) or result.get("status") not in {"success", "partial", "failed", "unavailable", "read"}:
                raise ValueError("executor returned invalid SkillResult")
            for key, kind in (("metrics", dict), ("artifacts", list), ("evidence", list), ("warnings", list)):
                if not isinstance(result.get(key), kind):
                    raise ValueError(f"invalid SkillResult.{key}")
            if result["status"] == "success" and manifest.execution_mode == "execute":
                produced = {ref.get("artifact_type") for ref in result["artifacts"] if isinstance(ref, dict)}
                missing = set(manifest.produces) - produced
                if missing or not result["evidence"]:
                    result["status"] = "partial"
                    result["warnings"].append("缺少声明产物或执行证据：" + ", ".join(sorted(missing)))
        except Exception as exc:
            result = output(context, {}, [], status="failed", warnings=[f"{type(exc).__name__}: {exc}"])
        result = json_value(result)
        result.update(schema_version="skill-execution-result-v2", skill_id=manifest.id, executor=manifest.id,
                      capabilities_executed=[manifest.id] if result.get("algorithm_invoked") else [],
                      duration_ms=round((perf_counter() - tick) * 1000, 3),
                      execution_state=execution_state_for(status=result["status"], invoked=result.get("algorithm_invoked", False), evidence_read=result["status"] == "read"),
                      suggested_next_skills=manifest.metadata.get("suggested_next_skills", []))
        result["audit"] = {"skill_id": manifest.id, "skill_version": manifest.version,
            "manifest_path": str(manifest.path), "manifest_hash": manifest.digest,
            "executor_module": manifest.executor["module"], "executor_function": manifest.executor["function"],
            "execution_mode": manifest.execution_mode, "input_refs": input_refs, "parameter_snapshot": parameters,
            "executor_invoked": invoked,
            "scene_context": scene,
            "dependency_runs": [{"skill_id": r["skill_id"], "status": r["status"],
                                 "manifest_hash": r.get("audit", {}).get("manifest_hash"),
                                 "execution_id": runtime_context["execution_id"]}
                                for r in runtime_context.get("results", []) if r["skill_id"] in manifest.depends_on],
            "started_at": started, "finished_at": datetime.now().astimezone().isoformat(),
            **{key: result[key] for key in ("metrics", "artifacts", "evidence", "warnings", "status")}}
        return result
