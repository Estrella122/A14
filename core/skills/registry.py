"""MD is authoritative; legacy is an explicit compatibility fallback."""
import logging
import os
import re
from pathlib import Path
from django.conf import settings
from .loader import ManifestError, scan_manifests


def manifest_mode():
    mode = getattr(settings, "SKILL_MANIFEST_MODE", os.getenv("SKILL_MANIFEST_MODE", "hybrid"))
    if mode not in {"md", "hybrid", "legacy"}:
        raise ManifestError(f"unknown SKILL_MANIFEST_MODE: {mode}")
    return mode


def tokens(text):
    text = str(text).lower()
    words = set(re.findall(r"[a-z][a-z0-9_]+", text)) | {
        chunk[i:i + 2] for chunk in re.findall(r"[\u4e00-\u9fff]+", text) for i in range(len(chunk) - 1)}
    return words - set("当前 数据 工业 用户 输出 输入 计算 检查 分析 估计 证据 参数 结果 异常 缺失 样本 是否 什么 时候 说明 是不 不是 有问 问题 训练 模型 建模 判断 适合 对当 前数 据估 对输 请对 进行 实际 指标 能力 条件 失败 不足 字段 使用 读取 执行 返回".split())


class SkillRegistry:
    def __init__(self):
        self._skills = {}
        self.stats = {}

    def register(self, skill):
        if skill.id in self._skills:
            raise ManifestError(f"duplicate skill id: {skill.id}")
        self._skills[skill.id] = skill

    def get(self, skill_id):
        return self._skills.get(skill_id)

    def list(self):
        return list(self._skills.values())

    def get_manifest(self, skill_id):
        skill = self.get(skill_id)
        return skill.public() if skill else None

    def get_prompt_content(self, skill_id):
        skill = self.get(skill_id)
        return getattr(skill, "body", "") if skill else ""

    def search(self, query):
        words = tokens(query)
        rows = []
        for skill in self.list():
            body = self.get_prompt_content(skill.id)
            if not body:
                continue
            intent_terms = skill.metadata.get("intent_terms", [])
            if intent_terms and not any(term.lower() in query.lower() for term in intent_terms):
                continue
            front = tokens(skill.name + " " + skill.metadata.get("description", ""))
            # Whole MD capability/use/input/output/limitation text participates.
            sections = re.split(r"(?m)^# ", body)
            positive_body = "\n".join(section for section in sections if not section.startswith(("不应该", "失败条件", "证据边界", "后续")))
            overlap = words & tokens(positive_body)
            lexical = any(t.lower() in query.lower() for t in skill.metadata.get("triggers", []))
            score = min(1.0, len(words & front) / 2) * .35 + min(1.0, len(overlap) / 3) * .55 + .1 * lexical
            if score:
                rows.append({"skill_id": skill.id, "score": round(score, 4), "body_terms": sorted(overlap),
                             "lexical_recall": lexical, "manifest_source": "SKILL.md",
                             "limitation_terms": sorted(words & (tokens(body) - tokens(positive_body)))})
        return sorted(rows, key=lambda row: (-row["score"], row["skill_id"]))

    def resolve_dependencies(self, selected, available_artifacts=None):
        ordered, visiting, visited = [], set(), set()
        def visit(key):
            if key in visiting:
                raise ManifestError(f"cyclic dependency: {key}")
            if key in visited:
                return
            skill = self.get(key)
            if not skill:
                raise ManifestError(f"missing dependency: {key}")
            visiting.add(key)
            # Existing immutable inputs can satisfy an upstream computation.
            # Graph validation (available_artifacts=None) always checks all edges.
            ready = available_artifacts is not None and bool(getattr(skill, "requires", [])) and set(skill.requires).issubset(available_artifacts)
            if not ready:
                for dependency in skill.depends_on:
                    visit(dependency)
            visiting.remove(key)
            visited.add(key)
            ordered.append(key)
        for key in selected:
            visit(key)
        return ordered

    def validate_dependency_graph(self):
        self.resolve_dependencies(self._skills)
        return True


def get_registry(mode=None, root=None):
    mode = mode or manifest_mode()
    registry = SkillRegistry()
    if mode != "legacy":
        manifests, registry.stats = scan_manifests(root or Path(__file__).parent)
        if registry.stats["invalid_skills"]:
            raise ManifestError("\n".join(registry.stats["invalid_skills"]))
        for skill in manifests:
            registry.register(skill)
    if mode != "md":
        from .catalog import SKILLS
        for skill in SKILLS:
            if not registry.get(skill.id):
                registry.register(skill)
    registry.validate_dependency_graph()
    registry.stats["registered_skills"] = len(registry.list())
    logging.getLogger(__name__).debug("Skill manifest load: %s", registry.stats)
    return registry
