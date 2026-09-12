from __future__ import annotations

from typing import Any, Iterable

from .capability_resolver import resolve_capabilities
from .skill_loader import DiscoveredSkill


def resolve_skills(
    task_spec: dict[str, Any],
    data_context: dict[str, Any],
    discovered_skills: Iterable[DiscoveredSkill],
    recalled_skill_ids: Iterable[str] = (),
    lexical_candidates: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Single resolution result for both Skill ownership and capabilities."""
    capability_resolution = resolve_capabilities(task_spec, data_context, recalled_skill_ids, lexical_candidates)
    selected_caps = set(capability_resolution["selected"])
    documentation_caps = set(capability_resolution["documentation"])
    requested_caps = selected_caps | documentation_caps
    skill_candidates = []
    selected_skills = []
    for skill in discovered_skills:
        owned = set(skill.manifest.get("capabilities", {}))
        matched = sorted(owned & requested_caps)
        semantic_fit = len(matched) / max(1, len(requested_caps))
        selected = bool(matched)
        item = {
            "skill_id": skill.name,
            "selected": selected,
            "matched_capabilities": matched,
            "semantic_fit": round(semantic_fit, 3),
            "context_fit": max((row["context_fit_score"] for row in capability_resolution["candidates"] if row["candidate"] in matched), default=0.0),
            "precondition_fit": max((row["data_precondition_score"] for row in capability_resolution["candidates"] if row["candidate"] in matched), default=0.0),
            "scene_fit": max((row["scene_fit_score"] for row in capability_resolution["candidates"] if row["candidate"] in matched), default=0.0),
            "dependency_fit": max((row["dependency_readiness_score"] for row in capability_resolution["candidates"] if row["candidate"] in matched), default=0.0),
            "artifact_readiness_score": max((row.get("artifact_readiness_score", 0.0) for row in capability_resolution["candidates"] if row["candidate"] in matched), default=0.0),
            "missing_artifacts": sorted({artifact for row in capability_resolution["candidates"] if row["candidate"] in matched for artifact in row.get("missing_artifacts", [])}),
            "evidence": capability_resolution["available_evidence"],
            "rejection_reason": None if selected else "该 Skill 不拥有 resolver 选中的 capability",
        }
        skill_candidates.append(item)
        if selected:
            selected_skills.append(skill.name)
    return {
        "selected_skills": selected_skills,
        "candidate_skills": skill_candidates,
        "rejected_skills": [item for item in skill_candidates if not item["selected"]],
        "selected_capabilities": capability_resolution["selected"],
        "blocked_capabilities": [row["candidate"] for row in capability_resolution["candidates"] if row["status"] == "blocked"],
        "skipped_capabilities": [row["candidate"] for row in capability_resolution["candidates"] if row["status"] == "deferred"],
        "documentation_capabilities": capability_resolution["documentation"],
        "reasoning_trace": capability_resolution["candidates"],
        "capability_resolution": capability_resolution,
    }
