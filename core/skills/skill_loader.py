from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable


MANIFEST_PATTERN = re.compile(r"<!--\s*skill-runtime-manifest\s*(\{.*?\})\s*-->", re.S)
FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
FRONTMATTER_FIELD = re.compile(r"^([a-zA-Z_][\w-]*):\s*(.*)$")


@dataclass(frozen=True)
class DiscoveredSkill:
    name: str
    description: str
    root: Path
    entrypoint: Path
    entrypoint_text: str | None
    manifest: dict[str, Any]


def _frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_PATTERN.search(text)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        field = FRONTMATTER_FIELD.match(line.strip())
        if field:
            result[field.group(1)] = field.group(2).strip().strip('"\'')
    return result


def _safe_declared_path(root: Path, relative_path: str) -> Path:
    declared = Path(str(relative_path))
    if declared.is_absolute():
        raise ValueError("Skill 声明不允许绝对路径")
    resolved_root = root.resolve()
    resolved = (resolved_root / declared).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError("Skill 声明路径越界")
    return resolved


def discover_skills(roots: Iterable[Path]) -> tuple[list[DiscoveredSkill], dict[str, Any]]:
    started = perf_counter()
    discovered: list[DiscoveredSkill] = []
    errors: list[dict[str, str]] = []
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for entrypoint in sorted(root.glob("*/SKILL.md")):
            try:
                sidecar = entrypoint.parent / "manifest.json"
                if sidecar.is_file():
                    manifest = json.loads(sidecar.read_text(encoding="utf-8"))
                    name = manifest.get("name")
                    if not name:
                        continue
                    discovered.append(DiscoveredSkill(name, manifest.get("description", ""), entrypoint.parent, entrypoint, None, manifest))
                    continue
                # Compatibility path for Skills that have not migrated to a
                # lightweight sidecar manifest yet.
                text = entrypoint.read_text(encoding="utf-8")
                metadata = _frontmatter(text)
                manifest_match = MANIFEST_PATTERN.search(text)
                if not metadata.get("name") or not manifest_match:
                    continue
                manifest = json.loads(manifest_match.group(1))
                discovered.append(DiscoveredSkill(metadata["name"], metadata.get("description", ""), entrypoint.parent, entrypoint, text, manifest))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append({"path": str(entrypoint), "error": type(exc).__name__})
    elapsed = round((perf_counter() - started) * 1000, 3)
    return discovered, {"skill_count": len(discovered), "scan_ms": elapsed, "errors": errors}


def _load_declared(skill: DiscoveredSkill, group: str, names: Iterable[str], errors: list[dict[str, str]]) -> list[dict[str, str]]:
    loaded = []
    declarations = skill.manifest.get(group, {})
    for name in names:
        declaration = declarations.get(name)
        if not isinstance(declaration, dict) or not declaration.get("path"):
            errors.append({"resource": f"{group}/{name}", "error": "undeclared"})
            continue
        try:
            path = _safe_declared_path(skill.root, declaration["path"])
            loaded.append({"name": name, "path": str(path.relative_to(skill.root)), "content": path.read_text(encoding="utf-8")})
        except (OSError, ValueError) as exc:
            errors.append({"resource": f"{group}/{name}", "error": type(exc).__name__})
    return loaded


def load_skill_context(
    message: str,
    roots: Iterable[Path],
    *,
    scene: str | None = None,
    selected_capabilities: Iterable[str] = (),
    selected_skill_name: str | None = None,
    task_kind: str = "data_analysis",
) -> dict[str, Any]:
    started = perf_counter()
    skills, discovery = discover_skills(roots)
    requested = set(selected_capabilities)
    selected_skill = None
    candidates = []
    if selected_skill_name:
        selected_skill = next((skill for skill in skills if skill.name == selected_skill_name), None)
    elif requested:
        selected_skill = next((skill for skill in skills if requested & set(skill.manifest.get("capabilities", {}))), None)
    empty = {
        "discovered_skills": [skill.name for skill in skills], "selected_skill": None,
        "loaded_capabilities": [], "loaded_workflows": [], "loaded_references": [], "invoked_scripts": [],
        "sources": [], "context": "", "errors": discovery["errors"],
        "performance": {**discovery, "loaded_skill_count": 0, "capability_count": 0, "context_characters": 0, "estimated_tokens": 0},
        "candidates": candidates,
    }
    if selected_skill is None:
        return empty

    errors = list(discovery["errors"])
    unknown = (scene or "").lower() in {"unknown", "unknown_scene"}
    safe_unknown = {"DATA_PROFILING", "DATA_QUALITY_ANALYSIS", "TREND_ANALYSIS", "TIME_SERIES_ANALYSIS", "CORRELATION_ANALYSIS", "ANOMALY_DETECTION", "MISSING_DATA_ANALYSIS"}
    if unknown:
        requested &= safe_unknown
    capabilities = _load_declared(selected_skill, "capabilities", sorted(requested), errors)
    workflow_names = ["generic-analysis"] if capabilities and task_kind != "knowledge_explanation" else []
    if unknown and task_kind != "knowledge_explanation":
        workflow_names.append("unknown-scene")
    if any(term in message.lower() for term in ("验证", "审计", "测试")):
        workflow_names.append("validation")
    reference_names = ["evidence-rules", "confidence-rules"] if capabilities else []
    if any(name in requested for name in {"ENERGY_ANALYSIS", "EQUIPMENT_HEALTH", "QUALITY_ANALYSIS", "OPERATING_STATE", "BOTTLENECK_ANALYSIS", "ROOT_CAUSE_CANDIDATES"}):
        reference_names.append("industrial-semantics")
    workflows = _load_declared(selected_skill, "workflows", workflow_names, errors)
    references = _load_declared(selected_skill, "references", reference_names, errors)
    scripts = selected_skill.manifest.get("scripts", {})
    invoked_scripts = []
    for name, declaration in scripts.items():
        if declaration.get("purpose") != "ANALYSIS_PLAN":
            continue
        try:
            script_path = _safe_declared_path(selected_skill.root, declaration.get("path", ""))
            if not script_path.is_file():
                raise FileNotFoundError(script_path)
            invoked_scripts.append(name)
        except (OSError, ValueError) as exc:
            errors.append({"resource": f"scripts/{name}", "error": type(exc).__name__})
    entrypoint_text = selected_skill.entrypoint_text
    if entrypoint_text is None:
        try:
            entrypoint_text = selected_skill.entrypoint.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append({"resource": "SKILL.md", "error": type(exc).__name__})
            entrypoint_text = ""
    effective_manifest = dict(selected_skill.manifest)
    detailed_manifest_match = MANIFEST_PATTERN.search(entrypoint_text)
    if detailed_manifest_match:
        try:
            detailed_manifest = json.loads(detailed_manifest_match.group(1))
            for key in ("input_requirements", "output_contract", "execution_policy", "evidence_policy", "dependencies"):
                if key in detailed_manifest:
                    effective_manifest[key] = detailed_manifest[key]
        except json.JSONDecodeError as exc:
            errors.append({"resource": "SKILL.md/manifest", "error": type(exc).__name__})
    parts = ([{"name": "SKILL.md", "path": "SKILL.md", "content": entrypoint_text}] if entrypoint_text else []) + capabilities + workflows + references
    context = "\n\n".join(f"[source: {item['path']}]\n{item['content']}" for item in parts)
    elapsed = round((perf_counter() - started) * 1000, 3)
    return {
        "discovered_skills": [skill.name for skill in skills], "selected_skill": selected_skill.name,
        "loaded_capabilities": [item["name"] for item in capabilities], "loaded_workflows": [item["name"] for item in workflows],
        "loaded_references": [item["name"] for item in references], "invoked_scripts": invoked_scripts,
        "sources": [item["path"] for item in parts], "context": context, "errors": errors, "candidates": candidates,
        "manifest": effective_manifest,
        "performance": {**discovery, "resolve_and_load_ms": elapsed, "loaded_skill_count": 1, "capability_count": len(capabilities), "context_characters": len(context), "estimated_tokens": (len(context) + 3) // 4},
    }


def default_skill_roots() -> tuple[Path, ...]:
    return (Path(__file__).resolve().parent,)
