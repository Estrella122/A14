"""Strict, local Markdown manifests. Legacy documents are reported separately."""
from dataclasses import dataclass
from hashlib import sha256
from importlib import import_module
from inspect import signature
from pathlib import Path
import re

import yaml


class ManifestError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        keys = [self.construct_object(key, deep=deep) for key, _ in node.value]
        if len(set(keys)) != len(keys):
            raise ManifestError("duplicate YAML key")
        return super().construct_mapping(node, deep=deep)


@dataclass(frozen=True)
class SkillManifest:
    metadata: dict
    body: str
    path: Path
    digest: str

    def __getattr__(self, key):
        if key in self.metadata:
            return self.metadata[key]
        if key == "handler":
            return "md"
        raise AttributeError(key)

    def public(self):
        contract = {"skill_id": self.id, "skill_type": self.category,
                    "executor": self.executor["module"], "capability": self.id,
                    "execution_mode": {"execute": "compute", "read": "evidence", "orchestration": "orchestrate"}.get(self.execution_mode, "evidence"),
                    "requires": self.requires, "produces": self.produces,
                    "quality_gates": self.metadata.get("quality_gates", []), "version": self.version}
        return {**self.metadata, "manifest_source": "SKILL.md", "manifest_path": str(self.path),
                "manifest_hash": self.digest, "manifest_version": self.version, "skill_doc": self.body,
                "handler": self.handler, "execution_contract": contract,
                "input_contract": self.requires, "output_contract": self.produces,
                "supported_scenarios": self.metadata.get("supported_scenarios", []),
                "task_types": self.metadata.get("task_types", ["INDUSTRIAL_ANALYSIS"]),
                "references": [], "related_references": [], "overlaps_with": [], "duplicate_of": None,
                "hardcoded_scene_or_field": False, "engineering_only": False}


def load_manifest(path):
    path = Path(path).resolve()
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", text, re.S)
    if not match:
        raise ManifestError(f"{path}: missing YAML front matter")
    try:
        data = yaml.load(match[1], Loader=UniqueLoader)
        if not isinstance(data, dict):
            raise ManifestError("manifest must be a mapping")
        for key in ("id", "name", "version", "category", "depends_on", "requires", "produces", "executor", "execution_mode"):
            if key not in data:
                raise ManifestError(f"missing field: {key}")
        for key in ("id", "name", "version", "category"):
            if not isinstance(data[key], str) or not data[key].strip():
                raise ManifestError(f"{key} must be a nonempty string")
        for key in ("depends_on", "requires", "produces", "triggers", "intent_terms", "suggested_next_skills", "evidence", "quality_gates"):
            values = data.get(key, [])
            if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
                raise ManifestError(f"{key} must be a list of strings")
        if data["execution_mode"] not in {"execute", "read", "orchestration", "unavailable"}:
            raise ManifestError("invalid execution_mode")
        parameters = data.get("parameters", [])
        if not isinstance(parameters, list) or any(not isinstance(p, dict) or not isinstance(p.get("name"), str) or p.get("type") not in {"float", "integer", "list", "string", "boolean"} for p in parameters):
            raise ManifestError("invalid parameter declarations")
        executor = data["executor"]
        if not isinstance(executor, dict) or executor.get("type") != "python":
            raise ManifestError("executor.type must be python")
        module, function = executor.get("module"), executor.get("function")
        if not isinstance(module, str) or not module.startswith("core.skills.") or not isinstance(function, str):
            raise ManifestError("executor must name a local core.skills module and function")
        if not callable(getattr(import_module(module), function, None)):
            raise ManifestError(f"executor function not callable: {module}.{function}")
        signature(getattr(import_module(module), function)).bind({}, {}, {})
        if not match[2].strip():
            raise ManifestError("Markdown body is required")
    except (yaml.YAMLError, ImportError, AttributeError, TypeError, ValueError) as exc:
        raise ManifestError(f"{path}: {exc}") from exc
    data.setdefault("workflow_scope", "workflow")
    data.setdefault("scope", "PROJECT")
    return SkillManifest(data, match[2], path, sha256(text.encode()).hexdigest())


def scan_manifests(root):
    manifests, errors, legacy = [], [], []
    for path in sorted(Path(root).rglob("SKILL.md")):
        text = path.read_text(encoding="utf-8")
        # Existing business docs and industrial-analysis have an older schema.
        # They remain visible in the load report, never counted as MD Skills.
        header = text.split("---", 2)[1] if text.startswith("---") and text.count("---") >= 2 else ""
        if not re.search(r"^id:", header, re.M) and (re.search(r"^business_skill_id:", header, re.M) or "skill-runtime-manifest" in text or (path.parent / "manifest.json").exists()):
            legacy.append(str(path))
            continue
        try:
            manifests.append(load_manifest(path))
        except (ManifestError, OSError) as exc:
            errors.append(str(exc))
    return manifests, {"loaded_skills": len(manifests), "invalid_skills": errors,
                       "legacy_documents": legacy, "duplicate_skills": [], "dependency_errors": []}
