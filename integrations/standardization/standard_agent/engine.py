from __future__ import annotations

import json
import csv
import math
import re
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd
from rapidfuzz import fuzz

from .repository import ROOT, ScenarioRepository, ScenarioTemplate
from .ml_model import semantic_core
from .point_dictionary import PointSemanticDictionary
from .semantic_ensemble import HybridSemanticModel
from .schema_validation import validate_standardized_frame
from .units import conversion, split_header_unit
from .physical_semantics import evaluate as evaluate_physical_semantics, final_field_acceptance_gate


def normalize_name(value: str) -> str:
    base, _ = split_header_unit(str(value))
    base = base.strip().lower()
    base = re.sub(r"[\s\-./\\:()（）\[\]【】]+", "_", base)
    return re.sub(r"_+", "_", base).strip("_")


def _ngrams(value: str, size: int = 2) -> Counter[str]:
    compact = normalize_name(value).replace("_", "")
    if len(compact) < size:
        return Counter([compact]) if compact else Counter()
    return Counter(compact[index : index + size] for index in range(len(compact) - size + 1))


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return dot / max(left_norm * right_norm, 1e-12)


def _is_opaque_instrument_tag(value: str) -> bool:
    """Return True for plant tags that contain no safe semantic field name.

    A code such as PT_8313A.AV_0 identifies a point inside one plant, but the
    number does not identify its process meaning outside that plant.  Such
    fields must be resolved by a tag dictionary or a human override.
    """
    normalized = normalize_name(value).rstrip("#")
    return bool(re.fullmatch(r"[a-z]{1,8}_?\d+[a-z]?(?:_av_?\d+)?", normalized))


class StandardizationAgent:
    def __init__(
        self,
        repository: ScenarioRepository | None = None,
        knowledge_path: Path | None = None,
        auto_threshold: float = 0.82,
        review_threshold: float = 0.62,
        model_path: Path | None = None,
    ) -> None:
        self.repository = repository or ScenarioRepository()
        self.knowledge_path = knowledge_path or ROOT / "knowledge" / "learned_aliases.json"
        self.auto_threshold = auto_threshold
        self.review_threshold = review_threshold
        self.model_path = model_path or ROOT / "models" / "field_semantic_model.json"
        self.encoder_path = ROOT / "models" / "embedding_encoder_multilingual"
        self.web_alias_path = ROOT / "knowledge" / "web_alias_candidates.csv"
        self.point_dictionary = PointSemanticDictionary(ROOT / "knowledge" / "point_semantics.csv")
        self.semantic_model = HybridSemanticModel.load(self.model_path, self.encoder_path) if self.model_path.exists() else None
        self._lock = threading.Lock()

    def _knowledge(self) -> dict[str, dict[str, list[str]]]:
        if not self.knowledge_path.exists():
            return {}
        return json.loads(self.knowledge_path.read_text(encoding="utf-8"))

    def learn_alias(self, scenario_id: str, raw_name: str, standard_name: str) -> dict[str, Any]:
        template = self.repository.get(scenario_id)
        if standard_name not in template.by_name:
            raise ValueError(f"场景 {scenario_id} 不存在标准字段 {standard_name}。")
        raw_name = str(raw_name).strip()
        if not raw_name:
            raise ValueError("原始字段名不能为空。")
        with self._lock:
            existing = self._aliases(template).get(normalize_name(raw_name))
            if existing and existing != standard_name:
                raise ValueError(f"别名 {raw_name} 已归属标准字段 {existing}，不能同时归属 {standard_name}。")
            knowledge = self._knowledge()
            scenario = knowledge.setdefault(scenario_id, {})
            aliases = scenario.setdefault(standard_name, [])
            if raw_name not in aliases:
                aliases.append(raw_name)
                aliases.sort()
            self.knowledge_path.parent.mkdir(parents=True, exist_ok=True)
            self.knowledge_path.write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"scenario_id": scenario_id, "raw_name": raw_name, "standard_name": standard_name, "learned": True}

    def forget_alias(self, scenario_id: str, raw_name: str, standard_name: str) -> dict[str, Any]:
        """Remove only a learned alias; template and audited web knowledge stay protected."""
        normalized = normalize_name(raw_name)
        removed = False
        with self._lock:
            knowledge = self._knowledge()
            aliases = knowledge.get(scenario_id, {}).get(standard_name, [])
            retained = [alias for alias in aliases if normalize_name(alias) != normalized]
            removed = len(retained) != len(aliases)
            if removed:
                if retained:
                    knowledge[scenario_id][standard_name] = retained
                else:
                    knowledge[scenario_id].pop(standard_name, None)
                    if not knowledge[scenario_id]:
                        knowledge.pop(scenario_id, None)
                self.knowledge_path.write_text(
                    json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        return {
            "scenario_id": scenario_id,
            "raw_name": raw_name,
            "standard_name": standard_name,
            "removed": removed,
        }

    def _aliases(self, template: ScenarioTemplate) -> dict[str, str]:
        index: dict[str, str] = {}

        def register(alias: str, standard_name: str) -> None:
            normalized = normalize_name(alias)
            if not normalized:
                return
            existing = index.get(normalized)
            if existing and existing != standard_name:
                raise ValueError(
                    f"场景 {template.scenario_id} 的别名 {alias} 同时指向 {existing} 和 {standard_name}。"
                )
            index[normalized] = standard_name

        learned = self._knowledge().get(template.scenario_id, {})
        for field in template.fields:
            candidates = [field.standard_name, field.display_name, *field.aliases, *learned.get(field.standard_name, [])]
            for alias in candidates:
                register(alias, field.standard_name)
        if self.web_alias_path.exists():
            with self.web_alias_path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    if row["scenario_id"] == template.scenario_id and row["review_status"] == "approved" and row["standard_name"] in template.by_name:
                        register(row["candidate_alias"], row["standard_name"])
        return index

    @staticmethod
    def _profile_series(
        series: pd.Series | None,
        definition: Any | None,
        detected_unit: str | None = None,
    ) -> dict[str, Any]:
        """Return bounded, deterministic evidence about values for semantic matching."""
        if series is None or definition is None:
            return {"available": False, "plausibility": 0.5, "missing_ratio": 0.0, "anomaly_ratio": 0.0}
        sample = series.iloc[:2000]
        total = max(len(sample), 1)
        missing_ratio = float(sample.isna().sum()) / total
        non_null = sample.dropna()
        if non_null.empty:
            return {"available": True, "plausibility": 0.0, "missing_ratio": 1.0, "anomaly_ratio": 0.0}
        if definition.data_type == "datetime":
            parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
            valid_ratio = float(parsed.notna().mean())
            changing = parsed.dropna().nunique() > 1
            plausibility = valid_ratio * (1.0 if changing else 0.75)
            anomaly_ratio = 1.0 - valid_ratio
        elif definition.data_type in {"float", "integer"}:
            numeric = pd.to_numeric(non_null, errors="coerce")
            valid = numeric.dropna()
            unit_conversion = conversion(detected_unit, definition.unit)
            if unit_conversion:
                valid = unit_conversion[1](valid)
            valid_ratio = float(numeric.notna().mean())
            violations = 0
            if definition.lower_bound is not None:
                violations += int((valid < definition.lower_bound).sum())
            if definition.upper_bound is not None:
                violations += int((valid > definition.upper_bound).sum())
            range_ratio = violations / max(len(valid), 1)
            integer_penalty = 0.0
            if definition.data_type == "integer" and len(valid):
                integer_penalty = float(((valid % 1) != 0).mean())
            anomaly_ratio = min(1.0, (1.0 - valid_ratio) + range_ratio + integer_penalty)
            plausibility = max(0.0, valid_ratio * (1.0 - range_ratio) * (1.0 - integer_penalty))
            if valid.nunique() <= 1:
                plausibility *= 0.92
        elif definition.data_type == "boolean":
            allowed = {"0", "1", "true", "false", "yes", "no", "y", "n", "是", "否", "有效", "无效"}
            valid_ratio = float(non_null.astype(str).str.strip().str.lower().isin(allowed).mean())
            plausibility, anomaly_ratio = valid_ratio, 1.0 - valid_ratio
        else:
            plausibility, anomaly_ratio = 0.85, 0.0
        return {
            "available": True,
            "plausibility": round(float(plausibility), 3),
            "missing_ratio": round(missing_ratio, 3),
            "anomaly_ratio": round(float(anomaly_ratio), 3),
            "changing": bool(non_null.nunique() > 1),
        }

    def _match_one(
        self,
        raw_name: str,
        template: ScenarioTemplate,
        series: pd.Series | None = None,
        neighbors: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        base_name, detected_unit = split_header_unit(raw_name)
        normalized = normalize_name(base_name)
        aliases = self._aliases(template)
        point_resolution = self.point_dictionary.resolve(raw_name, template.scenario_id, set(template.by_name))
        target = point_resolution.get("standard_field") if point_resolution["status"] == "resolved" else aliases.get(normalized)
        method = "alias"
        score = float(point_resolution["confidence"]) if point_resolution["status"] == "resolved" else (1.0 if target else 0.0)
        if point_resolution["status"] == "resolved":
            method = "point_dictionary"
        learned = self._knowledge().get(template.scenario_id, {})
        if target and any(
            normalize_name(alias) == normalized
            for alias in learned.get(target, [])
        ):
            method = "learned_alias"
        if target is None and template.config.get("physical_semantics"):
            # Formatting-only equality: preserve all letters and measurement digits.
            compact = normalized.replace("_", "")
            exact = {candidate for alias, candidate in aliases.items() if alias.replace("_", "") == compact}
            if len(exact) == 1:
                target = next(iter(exact))
                method = "normalized_alias"
                score = 1.0
        if target is None:
            core_targets: dict[str, set[str]] = {}
            for alias, candidate in aliases.items():
                core = semantic_core(alias)
                if core:
                    core_targets.setdefault(core, set()).add(candidate)
            raw_core = semantic_core(base_name)
            candidates = core_targets.get(raw_core, set())
            if len(candidates) == 1:
                target = next(iter(candidates))
                method = "vendor_core_alias"
                score = 0.96
        if target is None:
            source_grams = _ngrams(normalized)
            best: tuple[float, str | None] = (0.0, None)
            for alias, candidate in aliases.items():
                sequence = fuzz.WRatio(normalized, alias) / 100.0
                semantic = _cosine(source_grams, _ngrams(alias))
                candidate_score = 0.58 * sequence + 0.42 * semantic
                if candidate_score > best[0]:
                    best = (candidate_score, candidate)
            score, target = best
            method = "semantic"
        if self.semantic_model is not None and score < self.auto_threshold and (not template.config.get("physical_semantics") or method not in {"alias", "normalized_alias", "learned_alias", "point_dictionary"}):
            predictions = self.semantic_model.predict(base_name, template.scenario_id, limit=2)
            if predictions and predictions[0]["standard_name"] == "__irrelevant__" and predictions[0]["score"] >= float(self.semantic_model.metadata.get("accept_threshold", 0.54)):
                target = None
                score = 0.0
                method = "trained_reject"
            elif predictions and predictions[0]["score"] >= float(self.semantic_model.metadata.get("accept_threshold", 0.54)):
                runner_up = predictions[1]["score"] if len(predictions) > 1 else 0.0
                margin = predictions[0]["score"] - runner_up
                model_confidence = 0.82 + 0.18 * predictions[0]["score"] if margin >= 0.10 else 0.64 + 0.20 * predictions[0]["score"]
                if target is None or model_confidence > score:
                    target = predictions[0]["standard_name"]
                    score = model_confidence
                    method = "trained_model_auto" if margin >= 0.10 else "trained_model"
        if _is_opaque_instrument_tag(base_name) and method in {"semantic", "trained_model", "trained_model_auto"}:
            target = None
            score = 0.0
            method = "opaque_tag_requires_dictionary"
        if score < self.review_threshold:
            target = None
        definition = template.by_name.get(target) if target else None
        expected_unit = definition.unit if definition else None
        unit_conversion = conversion(detected_unit, expected_unit)
        unit_status = "not_declared"
        unit_action = None
        if detected_unit and expected_unit:
            if detected_unit == expected_unit:
                unit_status = "consistent"
            elif unit_conversion:
                unit_status = "convertible"
                unit_action = unit_conversion[0]
            else:
                unit_status = "conflict"
        value_profile = self._profile_series(series, definition, detected_unit)
        # Names nominate a field; units and values can veto or lower confidence.
        if target and unit_status == "conflict":
            score = min(score, 0.58)
        if target and value_profile["available"]:
            plausibility = float(value_profile["plausibility"])
            score *= 0.72 + 0.28 * plausibility
            # Missingness is data-quality evidence, not field-identity evidence.
            # An exact curated header such as vapour_pressure_kpa remains the
            # same field even when laboratory observations are intentionally
            # sparse.  Keep the penalty for inferred/fuzzy candidates only.
            if value_profile["missing_ratio"] >= 0.8 and method not in {"alias", "normalized_alias", "learned_alias", "point_dictionary"}:
                score *= 0.72
        physical = {}
        if template.config.get("physical_semantics") and target:
            physical = evaluate_physical_semantics(base_name, target, method, score, unit_status, template.config["physical_semantics"], self.auto_threshold)
        return {
            **physical,
            "source_column": raw_name,
            "candidate_field": target,
            "mapping_method": method,
            "raw": raw_name,
            "base_name": base_name,
            "standard": target,
            "display_name": definition.display_name if definition else None,
            "role": definition.role if definition else None,
            "data_type": definition.data_type if definition else None,
            "expected_unit": expected_unit,
            "detected_unit": detected_unit,
            "unit_status": unit_status,
            "unit_action": unit_action,
            "confidence": round(float(score), 3),
            "method": method,
            "value_profile": value_profile,
            "neighbor_fields": list(neighbors),
            "point_resolution": point_resolution,
        }

    def map_columns(self, columns: list[str], scenario_id: str, frame: pd.DataFrame | None = None, source_metadata: dict | None = None) -> dict[str, Any]:
        template = self.repository.get(scenario_id)
        names = [str(column) for column in columns]
        mappings = []
        for index, column in enumerate(names):
            neighbors = tuple(names[max(0, index - 2):index] + names[index + 1:index + 3])
            series = frame[column] if frame is not None and column in frame.columns else None
            mappings.append(self._match_one(column, template, series=series, neighbors=neighbors))
        for item in mappings:
            item.update(final_field_acceptance_gate(item, template, self.auto_threshold, (source_metadata or {}).get(item['raw'])))
        self._resolve_duplicates(mappings)
        self._annotate_relevance(mappings, template)
        for item in mappings:
            item["decision"] = "AUTO_ACCEPT" if item["status"] == "matched" else "REVIEW_REQUIRED" if item["status"] == "review" else "REJECT"
            item["decision_reason"] = item.get("physical_decision_reason", "existing identity/confidence/unit/value gates") + "; final status: " + item["status"]
            for dimension in ("semantic", "unit", "quantity_type", "role", "location", "direction"):
                item.setdefault(dimension + "_evidence", {"status": "not_evaluated", "reason": "no candidate or scenario has no physical contract"})
        required = {field.standard_name for field in template.fields if field.required}
        accepted = {item["standard"] for item in mappings if item["status"] == "matched"}
        candidates = {item["standard"] for item in mappings if item["status"] in {"matched", "review"}}
        return {
            "scenario_id": scenario_id,
            "scenario_name": template.scenario_name,
            "mappings": mappings,
            "missing_required": sorted(required - accepted),
            "required_coverage": round(len(required & accepted) / max(len(required), 1), 3),
            "candidate_coverage": round(len(required & candidates) / max(len(required), 1), 3),
            "auto_coverage": round(sum(item["status"] == "matched" for item in mappings) / max(len(columns), 1), 3),
            "review_count": sum(item["status"] == "review" for item in mappings),
            "unmapped_count": sum(item["status"] == "unmapped" for item in mappings),
            "unit_risk_count": sum(item["unit_status"] == "conflict" for item in mappings),
            "low_value_confidence_count": sum(
                item["value_profile"]["available"] and item["value_profile"]["plausibility"] < 0.6
                for item in mappings if item["standard"]
            ),
            "unresolved_points": [
                {
                    "point_id": item["point_resolution"]["point_id"],
                    "measurement_type_candidate": item["point_resolution"].get("measurement_type"),
                    "confidence": item["point_resolution"].get("confidence"),
                    "missing_knowledge": item["point_resolution"].get("missing_knowledge", []),
                }
                for item in mappings if item["point_resolution"]["status"] == "unresolved"
            ],
        }

    def detect_scenario(
        self,
        columns: list[str],
        instruction: str = "",
        selected_scenario_id: str | None = None,
        frame: pd.DataFrame | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ranked = []
        context = context or {}
        context_text = " ".join(str(value) for value in [instruction, context.get("source", ""), context.get("equipment", ""), context.get("process_module", "")]).lower()
        normalized_columns = {normalize_name(column) for column in columns}
        for template in self.repository.list():
            mapping = self.map_columns(columns, template.scenario_id, frame=frame)
            recognition = template.recognition
            usable = [item for item in mapping["mappings"] if item["standard"] and item["status"] in {"matched", "review"}]
            matched_names = {item["standard"] for item in usable}
            required = set(recognition["required_features"])
            supporting = set(recognition["supporting_features"])
            required_hits = sorted(required & matched_names)
            supporting_hits = sorted(supporting & matched_names)
            conflict_hits = sorted({
                pattern for pattern in recognition["conflicting_features"]
                if any(normalize_name(pattern) in column or column in normalize_name(pattern) for column in normalized_columns)
            })
            confidences = [float(item["confidence"]) for item in usable]
            unit_conflicts = [item["raw"] for item in usable if item["unit_status"] == "conflict"]
            abnormal_values = [item["raw"] for item in usable if item["value_profile"]["available"] and item["value_profile"]["anomaly_ratio"] >= 0.2]
            high_missing = [item["raw"] for item in usable if item["value_profile"]["available"] and item["value_profile"]["missing_ratio"] >= 0.5]
            keyword_hits = sum(keyword.lower() in context_text for keyword in template.config.get("keywords", []))
            evidence = ([f"required:{name}" for name in required_hits]
                        + [f"supporting:{name}" for name in supporting_hits]
                        + (["context:equipment_or_process"] if keyword_hits else []))
            conflicts = ([f"conflicting_feature:{name}" for name in conflict_hits]
                         + [f"unit_conflict:{name}" for name in unit_conflicts]
                         + [f"abnormal_values:{name}" for name in abnormal_values]
                         + [f"high_missing:{name}" for name in high_missing])
            required_coverage = len(required_hits) / max(len(required), 1)
            support_coverage = len(supporting_hits) / max(len(supporting), 1)
            mean_confidence = sum(confidences) / max(len(confidences), 1)
            evidence_count = len(required_hits) + len(supporting_hits)
            score = (0.47 * required_coverage + 0.18 * support_coverage + 0.22 * mean_confidence
                     + 0.08 * min(evidence_count / max(int(recognition["min_evidence"]), 1), 1.0)
                     + 0.05 * min(keyword_hits, 1))
            score -= 0.08 * len(conflict_hits) + 0.07 * len(unit_conflicts)
            score -= min(0.12, 0.03 * len(abnormal_values) + 0.02 * len(high_missing))
            if evidence_count < int(recognition["min_evidence"]):
                score = min(score, 0.42)
            score = max(0.0, min(score, 1.0))
            ranked.append({
                **template.summary(),
                "confidence": round(score, 3),
                "keyword_hits": keyword_hits,
                "matched_fields": sum(item["status"] == "matched" for item in mapping["mappings"]),
                "review_fields": mapping["review_count"],
                "required_coverage": mapping["required_coverage"],
                "missing_required": mapping["missing_required"],
                "score": round(score, 3),
                "evidence": evidence,
                "conflicts": conflicts,
                "evidence_count": evidence_count,
                "required_features": sorted(required),
                "supporting_features": sorted(supporting),
                "conflicting_features": list(recognition["conflicting_features"]),
                "minimum_evidence": int(recognition["min_evidence"]),
                "minimum_confidence": float(recognition["min_confidence"]),
                "minimum_required_coverage": float(recognition["min_required_coverage"]),
                "priority": int(recognition["priority"]),
            })
        ranked.sort(key=lambda item: (item["confidence"], item["priority"]), reverse=True)
        auto_selected = ranked[0]
        selected = auto_selected
        selection_source = "auto"
        if selected_scenario_id is not None:
            selected = next((item for item in ranked if item["scenario_id"] == selected_scenario_id), None)
            if selected is None:
                raise ValueError(f"未知场景：{selected_scenario_id}")
            selection_source = "manual"
        auto_margin = auto_selected["confidence"] - ranked[1]["confidence"] if len(ranked) > 1 else auto_selected["confidence"]
        selected_alternatives = [item["confidence"] for item in ranked if item["scenario_id"] != selected["scenario_id"]]
        selected_margin = selected["confidence"] - max(selected_alternatives, default=0.0)
        low_evidence = (selected["confidence"] < selected["minimum_confidence"]
                        or selected["evidence_count"] < selected["minimum_evidence"]
                        or selected["required_coverage"] < selected["minimum_required_coverage"])
        close_candidates = auto_margin < 0.08
        mixed_scenario_suspected = (
            len(ranked) > 1
            and (auto_margin < 0.12 or ranked[1]["confidence"] / max(ranked[0]["confidence"], 1e-9) >= 0.78)
            and ranked[1]["confidence"] >= ranked[1]["minimum_confidence"]
            and ranked[0]["matched_fields"] >= 3
            and ranked[1]["matched_fields"] >= 3
        )
        manual_disagreement = selection_source == "manual" and selected["scenario_id"] != auto_selected["scenario_id"] and selected_margin <= -0.08
        # Missingness and range anomalies are quality warnings.  They must not
        # turn an otherwise unique, exact scene identity into an ambiguous
        # scene; true semantic/identity conflicts still require review.
        evidence_conflict = any(
            str(item).startswith(("conflicting_feature:", "unit_conflict:"))
            for item in selected["conflicts"]
        )
        if low_evidence:
            ambiguity_reason = "场景证据不足"
        elif manual_disagreement:
            ambiguity_reason = "人工指定场景与自动识别结果不一致"
        elif mixed_scenario_suspected:
            ambiguity_reason = "检测到多个场景的字段簇"
        elif close_candidates:
            ambiguity_reason = "多个场景得分接近"
        elif evidence_conflict:
            ambiguity_reason = "字段单位、缺失率或数据范围存在冲突"
        else:
            ambiguity_reason = None
        scenario_groups = self._scenario_groups(columns, [item["scenario_id"] for item in ranked[:2]]) if mixed_scenario_suspected else []
        assigned_columns = {field["raw"] for group in scenario_groups for field in group["fields"]}
        if close_candidates and auto_selected["confidence"] >= 0.30:
            status, final_scene = "ambiguous", None
        elif low_evidence:
            status, final_scene = ("unknown" if selected["confidence"] < 0.30 else "uncertain"), None
        elif mixed_scenario_suspected or manual_disagreement:
            status, final_scene = "ambiguous", None
        elif selected["conflicts"]:
            status, final_scene = "uncertain", selected["scenario_id"]
        else:
            status, final_scene = "confirmed", selected["scenario_id"]
        return {
            "selected": selected,
            "auto_selected": auto_selected,
            "selection_source": selection_source,
            "candidates": ranked,
            "confidence_margin": round(auto_margin, 3),
            "auto_confidence_margin": round(auto_margin, 3),
            "selected_confidence_margin": round(selected_margin, 3),
            "is_ambiguous": low_evidence or close_candidates or mixed_scenario_suspected or manual_disagreement or evidence_conflict,
            "decision": "reject" if low_evidence else "review" if (close_candidates or mixed_scenario_suspected or manual_disagreement or evidence_conflict) else "accept",
            "is_out_of_scope": low_evidence,
            "ambiguity_reason": ambiguity_reason,
            "mixed_scenario": {
                "suspected": mixed_scenario_suspected,
                "candidate_scenarios": [item["scenario_id"] for item in ranked[:2]] if mixed_scenario_suspected else [],
                "groups": scenario_groups,
                "unassigned_columns": [str(column) for column in columns if str(column) not in assigned_columns] if mixed_scenario_suspected else [],
            },
            "scene_candidates": ranked,
            "final_scene": final_scene,
            "confidence": selected["confidence"],
            "status": status,
        }

    def _scenario_groups(self, columns: list[str], scenario_ids: list[str]) -> list[dict[str, Any]]:
        mappings = {scenario_id: self.map_columns(columns, scenario_id) for scenario_id in scenario_ids}
        groups = {
            scenario_id: {
                "scenario_id": scenario_id,
                "scenario_name": self.repository.get(scenario_id).scenario_name,
                "fields": [],
            }
            for scenario_id in scenario_ids
        }
        for raw in map(str, columns):
            choices = []
            for scenario_id in scenario_ids:
                item = next(entry for entry in mappings[scenario_id]["mappings"] if entry["raw"] == raw)
                if item["standard"] and item["status"] in {"matched", "review"}:
                    choices.append((float(item["confidence"]), scenario_id, item))
            choices.sort(reverse=True, key=lambda entry: entry[0])
            if not choices:
                continue
            if len(choices) > 1 and choices[0][0] - choices[1][0] < 0.08:
                continue
            _, scenario_id, item = choices[0]
            groups[scenario_id]["fields"].append({
                "raw": raw,
                "standard": item["standard"],
                "display_name": item["display_name"],
                "confidence": item["confidence"],
                "status": item["status"],
                "detected_unit": item["detected_unit"],
                "expected_unit": item["expected_unit"],
            })
        return [
            {**group, "field_count": len(group["fields"])}
            for group in groups.values()
            if group["fields"]
        ]

    def standardize(
        self,
        frame: pd.DataFrame,
        scenario_id: str = "auto",
        instruction: str = "",
        overrides: dict[str, str] | None = None,
        convert_units: bool = True,
        include_unmapped: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        standardization_started = perf_counter()
        standardization_started_at = datetime.now().astimezone().isoformat(timespec="milliseconds")
        if frame.empty:
            raise ValueError("CSV 数据为空。")
        duplicate_columns = [str(name) for name, count in Counter(map(str, frame.columns)).items() if count > 1]
        if duplicate_columns:
            raise ValueError("原始 CSV 存在重复列名：" + "、".join(duplicate_columns))
        detection = self.detect_scenario(
            list(frame.columns),
            instruction,
            selected_scenario_id=None if scenario_id == "auto" else scenario_id,
            frame=frame,
            context=context,
        )
        selected_id = detection["selected"]["scenario_id"] if scenario_id == "auto" else scenario_id
        template = self.repository.get(selected_id)
        derived_fields: list[dict[str, Any]] = []
        time_derivation = template.config.get("time_derivation") or {}
        timestamp_field = template.config.get("timestamp_field")
        source_time_field = time_derivation.get("source_field")
        if timestamp_field not in frame.columns and source_time_field in frame.columns:
            values = pd.to_numeric(frame[source_time_field], errors="coerce")
            unit = str(time_derivation.get("unit") or "h")
            origin = pd.Timestamp(str(time_derivation.get("origin") or "2000-01-01T00:00:00"))
            derived = origin + pd.to_timedelta(values, unit=unit)
            if int(derived.notna().sum()) == int(values.notna().sum()) and derived.notna().sum() >= 2:
                frame = frame.copy()
                frame[timestamp_field] = derived
                derived_fields.append({
                    "field": timestamp_field,
                    "source_field": source_time_field,
                    "method": "relative_elapsed_time_to_datetime",
                    "origin": str(origin),
                    "unit": unit,
                    "physical_time_claim": "relative_only",
                })
                detection = self.detect_scenario(
                    list(frame.columns), instruction, selected_scenario_id=selected_id,
                    frame=frame, context=context,
                )
        scene_recognition_ms = round((perf_counter() - standardization_started) * 1000, 3)
        scene_recognition_finished_at = datetime.now().astimezone().isoformat(timespec="milliseconds")
        mapping_started = perf_counter()
        mapping_started_at = datetime.now().astimezone().isoformat(timespec="milliseconds")
        mapping = self.map_columns(list(frame.columns), selected_id, frame=frame, source_metadata=(context or {}).get("field_metadata"))
        overrides = overrides or {}
        for item in mapping["mappings"]:
            if item["raw"] in overrides:
                target = overrides[item["raw"]]
                if target == "__ignore__":
                    item.update(standard=None, display_name=None, role=None, data_type=None,
                                expected_unit=None, confidence=1.0, method="manual_ignore", status="unmapped",
                                unit_status="not_declared", unit_action=None)
                    continue
                definition = template.by_name.get(target)
                if definition is None:
                    raise ValueError(f"人工指定了不存在的标准字段：{target}")
                item.update(
                    standard=target,
                    display_name=definition.display_name,
                    role=definition.role,
                    data_type=definition.data_type,
                    expected_unit=definition.unit,
                    confidence=1.0,
                    method="manual",
                    status="matched",
                )
                unit_conversion = conversion(item["detected_unit"], definition.unit)
                if not item["detected_unit"]:
                    item.update(unit_status="not_declared", unit_action=None)
                elif item["detected_unit"] == definition.unit:
                    item.update(unit_status="consistent", unit_action=None)
                elif unit_conversion:
                    item.update(unit_status="convertible", unit_action=unit_conversion[0])
                else:
                    item.update(unit_status="conflict", unit_action=None)
        for item in mapping["mappings"]:
            item.update(final_field_acceptance_gate(item, template, self.auto_threshold, (context or {}).get("field_metadata", {}).get(item["raw"])))
        self._resolve_duplicates(mapping["mappings"])
        self._annotate_relevance(mapping["mappings"], template)
        result = pd.DataFrame(index=frame.index)
        accepted = []
        conversions = []
        skipped_conversions = []
        validation = []
        for item in mapping["mappings"]:
            if item["status"] != "matched" or not item["standard"]:
                if include_unmapped:
                    result[item["raw"]] = frame[item["raw"]]
                continue
            definition = template.by_name[item["standard"]]
            series = frame[item["raw"]].copy()
            unit_conversion = conversion(item["detected_unit"], item["expected_unit"])
            conversion_errors = 0
            if convert_units and unit_conversion:
                numeric = pd.to_numeric(series, errors="coerce")
                conversion_errors = max(int(series.notna().sum()) - int(numeric.notna().sum()), 0)
                series = unit_conversion[1](numeric)
                conversions.append({"field": item["standard"], "source_unit": item["detected_unit"], "target_unit": item["expected_unit"], "formula": unit_conversion[0]})
            elif not convert_units and unit_conversion:
                skipped_conversions.append({"field": item["standard"], "source_unit": item["detected_unit"], "target_unit": item["expected_unit"], "formula": unit_conversion[0]})
            series, type_errors = self._coerce_type(series, definition.data_type)
            type_errors += conversion_errors
            bounds_violations = 0
            bounds_checked = item["unit_status"] in {"consistent", "not_declared"} or bool(convert_units and unit_conversion)
            if definition.data_type in {"float", "integer"} and bounds_checked:
                if definition.lower_bound is not None:
                    bounds_violations += int((series < definition.lower_bound).fillna(False).sum())
                if definition.upper_bound is not None:
                    bounds_violations += int((series > definition.upper_bound).fillna(False).sum())
            validation.append(
                {
                    "field": definition.standard_name,
                    "data_type": definition.data_type,
                    "type_errors": type_errors,
                    "bounds_violations": bounds_violations,
                    "bounds_checked": bounds_checked,
                    "bounds_skip_reason": None if bounds_checked else "单位未统一，不与标准单位物理范围比较",
                    "lower_bound": definition.lower_bound,
                    "upper_bound": definition.upper_bound,
                }
            )
            result[item["standard"]] = series
            accepted.append(item["standard"])
        ordered = [field.standard_name for field in template.fields if field.standard_name in result.columns]
        extras = [column for column in result.columns if column not in ordered]
        result = result[ordered + extras]
        required = {field.standard_name for field in template.fields if field.required}
        mapping["missing_required"] = sorted(required - set(accepted))
        mapping["required_coverage"] = round(len(required & set(accepted)) / max(len(required), 1), 3)
        mapping["review_count"] = sum(item["status"] == "review" for item in mapping["mappings"])
        mapping["unmapped_count"] = sum(item["status"] == "unmapped" for item in mapping["mappings"])
        mapping["unit_risk_count"] = sum(item["unit_status"] == "conflict" for item in mapping["mappings"])
        mapping["unit_conversion_required_count"] = len(skipped_conversions)
        issues = self._issues(mapping)
        for item in skipped_conversions:
            issues.append({
                "level": "error",
                "code": "UNIT_CONVERSION_REQUIRED",
                "field": item["field"],
                "message": f"已关闭自动换算；{item['source_unit']} 数值未转为标准单位 {item['target_unit']}",
            })
        for item in validation:
            if item["type_errors"]:
                issues.append({"level": "error", "code": "TYPE_ERROR", "field": item["field"], "message": f"{item['type_errors']} 个值无法转换为 {item['data_type']}"})
            if item["bounds_violations"]:
                issues.append({"level": "warning", "code": "OUT_OF_RANGE", "field": item["field"], "message": f"{item['bounds_violations']} 个值超出模板物理范围；仅标记，未清洗"})
        schema_validation = validate_standardized_frame(result, template)
        if not schema_validation["passed"]:
            issues.append({
                "level": "error",
                "code": "SCHEMA_CONTRACT_FAILED",
                "field": template.scenario_id,
                "message": f"场景数据契约存在 {schema_validation['failure_count']} 项失败，需复核后再交付",
            })
        data_decision = self._data_decision(mapping, detection, validation, schema_validation)
        total_ms = round((perf_counter() - standardization_started) * 1000, 3)
        field_standardization_ms = round((perf_counter() - mapping_started) * 1000, 3)
        standardization_finished_at = datetime.now().astimezone().isoformat(timespec="milliseconds")
        return {
            "scenario": template.summary(),
            "detection": detection,
            "mapping": mapping,
            "conversions": conversions,
            "derived_fields": derived_fields,
            "skipped_conversions": skipped_conversions,
            "validation": validation,
            "schema_validation": schema_validation,
            "issues": issues,
            "data_decision": data_decision,
            "standardized_data": result,
            "dictionary": [field.as_dict() for field in template.fields],
            "performance_trace": {
                "scene_recognition_ms": scene_recognition_ms,
                "field_standardization_ms": field_standardization_ms,
                "standardization_total_ms": total_ms,
            },
            "performance_spans": {
                "scene_recognition": {"start_time": standardization_started_at, "end_time": scene_recognition_finished_at, "elapsed_ms": scene_recognition_ms},
                "field_standardization": {"start_time": mapping_started_at, "end_time": standardization_finished_at, "elapsed_ms": field_standardization_ms},
                "standardization": {"start_time": standardization_started_at, "end_time": standardization_finished_at, "elapsed_ms": total_ms},
            },
        }

    def _resolve_duplicates(self, mappings: list[dict[str, Any]]) -> None:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in mappings:
            if item["standard"]:
                grouped.setdefault(item["standard"], []).append(item)
        for items in grouped.values():
            if len(items) < 2:
                continue
            winner = max(items, key=lambda item: (item.get("physical_gate_pass", False), item["method"] == "manual", item["confidence"]))
            for item in items:
                item["status"] = "matched" if item is winner and item["confidence"] >= self.auto_threshold and item.get("physical_gate_pass", False) else ("review" if item is winner else "duplicate")

        for item in mappings:
            item['decision'] = 'AUTO_ACCEPT' if item.get('status') == 'matched' else 'REVIEW_REQUIRED' if item.get('status') == 'review' else 'REJECT'
            if 'final_acceptance_audit' in item:
                item['final_acceptance_audit']['final_status'] = item.get('status')
                item['final_acceptance_audit']['post_duplicate_decision'] = item['decision']

    @staticmethod
    def _annotate_relevance(mappings: list[dict[str, Any]], template: ScenarioTemplate) -> None:
        for item in mappings:
            definition = template.by_name.get(item.get("standard"))
            if item["status"] == "matched" and definition:
                item["need_level"] = "required" if definition.required else "useful"
                item["is_needed"] = True
            elif item["status"] in {"review", "duplicate"}:
                item["need_level"] = "uncertain"
                item["is_needed"] = None
            else:
                item["need_level"] = "irrelevant"
                item["is_needed"] = False

    @staticmethod
    def _data_decision(
        mapping: dict[str, Any],
        detection: dict[str, Any],
        validation: list[dict[str, Any]],
        schema_validation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        confidence = float(detection["selected"]["confidence"])
        coverage = float(mapping["required_coverage"])
        type_errors = sum(item["type_errors"] for item in validation)
        conversion_required = int(mapping.get("unit_conversion_required_count", 0))
        ambiguous = bool(detection.get("is_ambiguous"))
        schema_failed = bool(schema_validation and not schema_validation.get("passed", False))
        if ambiguous and (confidence < 0.35 or coverage < 0.5):
            status = "reject"
        elif ambiguous:
            status = "review"
        elif coverage == 1.0 and mapping["unit_risk_count"] == 0 and mapping["review_count"] == 0 and conversion_required == 0:
            status = "ready" if type_errors == 0 and not schema_failed else "review"
        elif confidence >= 0.45 and coverage >= 0.5:
            status = "review"
        else:
            status = "reject"
        reasons = []
        if ambiguous:
            reasons.append(f"场景判定不明确：{detection.get('ambiguity_reason') or '需要人工确认'}（领先差 {detection.get('auto_confidence_margin', 0):.1%}）")
        if mapping["missing_required"]:
            reasons.append("缺少必需字段：" + "、".join(mapping["missing_required"]))
        if mapping["review_count"]:
            reasons.append(f"{mapping['review_count']} 个字段需要人工确认")
        if mapping["unit_risk_count"]:
            reasons.append(f"{mapping['unit_risk_count']} 个单位冲突")
        if conversion_required:
            reasons.append(f"{conversion_required} 个字段需要单位换算，但本次已关闭自动换算")
        if type_errors:
            reasons.append(f"{type_errors} 个类型转换错误")
        if schema_failed:
            reasons.append(f"场景数据契约存在 {schema_validation.get('failure_count', 0)} 项失败")
        if not reasons:
            reasons.append("场景明确且必需字段完整，可交付下游模块")
        return {
            "status": status,
            "is_usable": status == "ready",
            "scenario_confidence": confidence,
            "required_coverage": coverage,
            "reasons": reasons,
        }

    @staticmethod
    def _coerce_type(series: pd.Series, data_type: str) -> tuple[pd.Series, int]:
        original_non_null = int(series.notna().sum())
        if data_type == "datetime":
            converted = pd.to_datetime(series, errors="coerce", format="mixed")
            if not pd.api.types.is_numeric_dtype(series):
                day_first = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=True)
                if int(day_first.notna().sum()) > int(converted.notna().sum()):
                    converted = day_first
        elif data_type in {"float", "integer"}:
            converted = pd.to_numeric(series, errors="coerce")
            if data_type == "integer":
                fractional = converted.notna() & (converted % 1 != 0)
                converted = converted.mask(fractional)
                converted = converted.astype("Int64")
        elif data_type == "boolean":
            truthy = {"1", "true", "yes", "y", "是", "有效"}
            falsy = {"0", "false", "no", "n", "否", "无效"}
            def parse(value):
                if pd.isna(value):
                    return pd.NA
                normalized = str(value).strip().lower()
                if normalized in truthy:
                    return True
                if normalized in falsy:
                    return False
                return pd.NA
            converted = series.map(parse).astype("boolean")
        elif data_type in {"string", "category"}:
            converted = series.astype("string")
            if data_type == "category":
                converted = converted.astype("category")
        else:
            converted = series
        errors = max(original_non_null - int(converted.notna().sum()), 0)
        return converted, errors

    @staticmethod
    def _issues(mapping: dict[str, Any]) -> list[dict[str, str]]:
        issues = []
        for field in mapping["missing_required"]:
            issues.append({"level": "error", "code": "MISSING_REQUIRED", "field": field, "message": "场景必需字段缺失"})
        for item in mapping["mappings"]:
            if item["status"] == "review":
                issues.append({"level": "warning", "code": "REVIEW_MAPPING", "field": item["raw"], "message": f"候选字段 {item['standard']} 需要人工确认"})
            elif item["status"] == "duplicate":
                issues.append({"level": "warning", "code": "DUPLICATE_TARGET", "field": item["raw"], "message": f"与其他字段重复映射到 {item['standard']}"})
            elif item["status"] == "unmapped":
                issues.append({"level": "info", "code": "UNMAPPED", "field": item["raw"], "message": "未纳入当前场景标准"})
            if item["unit_status"] == "conflict":
                issues.append({"level": "error", "code": "UNIT_CONFLICT", "field": item["raw"], "message": f"单位 {item['detected_unit']} 无法自动转换为 {item['expected_unit']}"})
        return issues


def public_result(result: dict[str, Any], preview_rows: int = 12) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            **result,
            "preview": result["standardized_data"].head(preview_rows).fillna("").astype(str).to_dict(orient="records"),
            "standardized_columns": list(result["standardized_data"].columns),
            "standardized_rows": len(result["standardized_data"]),
        }.items()
        if key != "standardized_data"
    }
