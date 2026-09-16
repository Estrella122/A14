from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIELD_COLUMNS = {
    "standard_name", "display_name", "description", "role", "data_type",
    "unit", "required", "aliases", "lower_bound", "upper_bound",
}


@dataclass(frozen=True)
class FieldDefinition:
    standard_name: str
    display_name: str
    description: str
    role: str
    data_type: str
    unit: str
    required: bool
    aliases: tuple[str, ...]
    lower_bound: float | None
    upper_bound: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "standard_name": self.standard_name,
            "display_name": self.display_name,
            "description": self.description,
            "role": self.role,
            "data_type": self.data_type,
            "unit": self.unit,
            "required": self.required,
            "aliases": list(self.aliases),
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
        }


@dataclass(frozen=True)
class ScenarioTemplate:
    config: dict[str, Any]
    fields: tuple[FieldDefinition, ...]

    @property
    def scenario_id(self) -> str:
        return str(self.config["scenario_id"])

    @property
    def scenario_name(self) -> str:
        return str(self.config["scenario_name"])

    @property
    def by_name(self) -> dict[str, FieldDefinition]:
        return {field.standard_name: field for field in self.fields}

    @property
    def recognition(self) -> dict[str, Any]:
        configured = self.config.get("recognition", {})
        required = [field.standard_name for field in self.fields if field.required]
        optional = [field.standard_name for field in self.fields if not field.required]
        return {
            "required_features": configured.get("required_features", required),
            "supporting_features": configured.get("supporting_features", optional),
            "conflicting_features": configured.get("conflicting_features", []),
            "priority": configured.get("priority", 0),
            "min_evidence": configured.get("minimum_evidence", configured.get("min_evidence", min(3, max(2, len(required))))),
            "min_confidence": configured.get("minimum_confidence", configured.get("min_confidence", 0.52)),
            "min_required_coverage": configured.get("minimum_required_field_coverage", configured.get("min_required_coverage", 0.55)),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "industry": self.config.get("industry", ""),
            "process_unit": self.config.get("process_unit", ""),
            "version": self.config.get("version", ""),
            "field_count": len(self.fields),
            "required_count": sum(field.required for field in self.fields),
            "primary_output": self.config.get("primary_output"),
            "model_outputs": self.config.get("model_outputs", [self.config.get("primary_output")]),
            "selection_window_samples": self.config.get("selection_window_samples", 30),
            "selection_step_samples": self.config.get("selection_step_samples", 15),
            "time_axis_type": self.config.get("time_axis_type", "wall_clock"),
            "sampling_seconds": self.config.get("sampling_seconds"),
            "recommended_max_lag": self.config.get("recommended_max_lag"),
            "alignment_policy": self.config.get("alignment_policy"),
            "lab_tolerance_hours": self.config.get("lab_tolerance_hours"),
            "measurement_delay_minutes": self.config.get("measurement_delay_minutes"),
            "expected_rows": self.config.get("expected_rows"),
            "source": self.config.get("source"),
            "data_provenance_required": self.config.get("data_provenance_required", []),
            "algorithm_profile": self.config.get("algorithm_profile", {}),
            "notes": self.config.get("notes", ""),
        }


def _number(value: str) -> float | None:
    value = str(value or "").strip()
    return float(value) if value else None


class ScenarioRepository:
    def __init__(self, standards_root: Path | None = None) -> None:
        self.root = standards_root or ROOT / "standards"
        self.global_schema = json.loads((self.root / "global_schema.json").read_text(encoding="utf-8"))
        self._templates = self._load_templates()

    def _load_templates(self) -> dict[str, ScenarioTemplate]:
        templates: dict[str, ScenarioTemplate] = {}
        for template_path in sorted((self.root / "scenarios").glob("*/template.json")):
            config = json.loads(template_path.read_text(encoding="utf-8"))
            dictionary_path = template_path.parent / config["dictionary"]
            fields = []
            with dictionary_path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                missing_columns = sorted(FIELD_COLUMNS - set(reader.fieldnames or []))
                if missing_columns:
                    raise ValueError(f"{dictionary_path} 缺少字典列：{missing_columns}")
                for row in reader:
                    fields.append(
                        FieldDefinition(
                            standard_name=row["standard_name"].strip(),
                            display_name=row["display_name"].strip(),
                            description=row["description"].strip(),
                            role=row["role"].strip(),
                            data_type=row["data_type"].strip(),
                            unit=row["unit"].strip(),
                            required=row["required"].strip().lower() == "true",
                            aliases=tuple(value.strip() for value in row["aliases"].split("|") if value.strip()),
                            lower_bound=_number(row.get("lower_bound", "")),
                            upper_bound=_number(row.get("upper_bound", "")),
                        )
                    )
            template = ScenarioTemplate(config=config, fields=tuple(fields))
            self._validate(template)
            if template.scenario_id in templates:
                raise ValueError(f"场景 ID 重复：{template.scenario_id}")
            templates[template.scenario_id] = template
        if not templates:
            raise ValueError("未发现任何场景模板。")
        return templates

    def _validate(self, template: ScenarioTemplate) -> None:
        if not template.fields:
            raise ValueError(f"{template.scenario_id} 字段字典为空。")
        names = [field.standard_name for field in template.fields]
        if len(names) != len(set(names)):
            raise ValueError(f"{template.scenario_id} 存在重复标准字段。")
        roles = set(self.global_schema["variable_roles"])
        invalid_roles = sorted({field.role for field in template.fields} - roles)
        if invalid_roles:
            raise ValueError(f"{template.scenario_id} 存在非法变量角色：{invalid_roles}")
        invalid_names = sorted(name for name in names if not re.fullmatch(r"[a-z][a-z0-9_]*", name))
        if invalid_names:
            raise ValueError(f"{template.scenario_id} 存在非 lower_snake_case 字段：{invalid_names}")
        supported_types = set(self.global_schema["supported_data_types"])
        invalid_types = sorted({field.data_type for field in template.fields} - supported_types)
        if invalid_types:
            raise ValueError(f"{template.scenario_id} 存在非法数据类型：{invalid_types}")
        allowed_units = set(self.global_schema.get("allowed_units", []))
        invalid_units = sorted({field.unit for field in template.fields} - allowed_units)
        if invalid_units:
            raise ValueError(f"{template.scenario_id} 存在未登记标准单位：{invalid_units}")
        invalid_bounds = [
            field.standard_name for field in template.fields
            if field.lower_bound is not None and field.upper_bound is not None and field.lower_bound > field.upper_bound
        ]
        if invalid_bounds:
            raise ValueError(f"{template.scenario_id} 存在上下限倒置字段：{invalid_bounds}")
        recognition = template.recognition
        referenced = set(recognition["required_features"]) | set(recognition["supporting_features"])
        unknown_features = sorted(referenced - set(names))
        if unknown_features:
            raise ValueError(f"{template.scenario_id} 的识别规则引用未知字段：{unknown_features}")
        if int(recognition["min_evidence"]) < 2:
            raise ValueError(f"{template.scenario_id} 的 min_evidence 不能小于 2。")
        required = {template.config.get("timestamp_field"), template.config.get("primary_output")}
        if not required.issubset(set(names)):
            raise ValueError(f"{template.scenario_id} 缺少时间字段或主输出字段。")
        timestamp = template.by_name[template.config["timestamp_field"]]
        if timestamp.role != "time" or timestamp.data_type != "datetime" or not timestamp.required:
            raise ValueError(f"{template.scenario_id} 的时间字段必须为 required datetime/time。")
        primary_output = template.by_name[template.config["primary_output"]]
        if primary_output.role != "controlled" or not primary_output.required:
            raise ValueError(f"{template.scenario_id} 的主输出必须为 required controlled 字段。")
        model_outputs = template.config.get("model_outputs", [template.config["primary_output"]])
        invalid_outputs = [name for name in model_outputs if name not in template.by_name or template.by_name[name].role != "controlled"]
        if invalid_outputs:
            raise ValueError(f"{template.scenario_id} 的模型输出必须全部是 controlled 字段：{invalid_outputs}")
        profile = template.config.get("algorithm_profile", {})
        if profile:
            selection = profile.get("selection", {})
            weights = selection.get("score_weights", {})
            if weights and abs(sum(float(value) for value in weights.values()) - 1.0) > 1e-9:
                raise ValueError(f"{template.scenario_id} 的动态评分权重之和必须为1。")
            if int(selection.get("window_samples", 15)) < 15:
                raise ValueError(f"{template.scenario_id} 的动态窗口不能小于15个样本。")
            if int(selection.get("step_samples", 1)) > int(selection.get("window_samples", 15)):
                raise ValueError(f"{template.scenario_id} 的动态窗口步长不能大于窗口。")
            decoupling = profile.get("decoupling", {})
            if not 1 <= int(decoupling.get("max_lag_samples", 60)) <= 600:
                raise ValueError(f"{template.scenario_id} 的最大时滞必须在1到600之间。")
            optimization = profile.get("optimization", {})
            objective_weights = optimization.get("objective_weights", {})
            if objective_weights and abs(sum(float(value) for value in objective_weights.values()) - 1.0) > 1e-9:
                raise ValueError(f"{template.scenario_id} 的寻优目标权重之和必须为1。")
            bounds = optimization.get("bounds", {})
            for candidate in optimization.get("candidates", []):
                for parameter in ("top_k", "max_lag"):
                    rule = bounds.get(parameter)
                    if rule and not float(rule["min"]) <= float(candidate[parameter]) <= float(rule["max"]):
                        raise ValueError(f"{template.scenario_id} 的候选{candidate.get('round')}超出{parameter}边界。")
        alias_index: dict[str, str] = {}
        for field in template.fields:
            for alias in (field.standard_name, field.display_name, *field.aliases):
                normalized = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", alias.lower())
                if not normalized:
                    continue
                existing = alias_index.get(normalized)
                if existing and existing != field.standard_name:
                    raise ValueError(f"{template.scenario_id} 的别名 {alias} 同时指向 {existing} 和 {field.standard_name}。")
                alias_index[normalized] = field.standard_name

    def list(self) -> list[ScenarioTemplate]:
        return list(self._templates.values())

    def get(self, scenario_id: str) -> ScenarioTemplate:
        try:
            return self._templates[scenario_id]
        except KeyError as exc:
            raise ValueError(f"未知场景：{scenario_id}") from exc
