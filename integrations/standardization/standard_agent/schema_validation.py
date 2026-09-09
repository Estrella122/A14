from __future__ import annotations

from typing import Any

import pandas as pd
import pandera.pandas as pa

from .repository import ScenarioTemplate


PANDERA_DTYPES: dict[str, Any] = {
    "float": pa.Float,
    "integer": pa.Int,
    "string": pa.String,
    "category": pa.String,
    "boolean": pa.Bool,
    "datetime": pa.DateTime,
}


def build_frame_schema(template: ScenarioTemplate) -> pa.DataFrameSchema:
    columns = {}
    for field in template.fields:
        checks = []
        if field.data_type in {"float", "integer"}:
            if field.lower_bound is not None:
                checks.append(pa.Check.ge(field.lower_bound))
            if field.upper_bound is not None:
                checks.append(pa.Check.le(field.upper_bound))
        columns[field.standard_name] = pa.Column(
            PANDERA_DTYPES[field.data_type],
            checks=checks,
            nullable=True,
            required=field.required,
            coerce=True,
        )
    return pa.DataFrameSchema(columns, strict=False, coerce=False, name=template.scenario_id)


def validate_standardized_frame(frame: pd.DataFrame, template: ScenarioTemplate) -> dict[str, Any]:
    schema = build_frame_schema(template)
    try:
        schema.validate(frame, lazy=True)
        failures: list[dict[str, Any]] = []
    except pa.errors.SchemaErrors as exc:
        failures = []
        for item in exc.failure_cases.fillna("").to_dict(orient="records"):
            failures.append({key: str(value) for key, value in item.items()})
    return {
        "engine": "pandera",
        "schema": template.scenario_id,
        "passed": not failures,
        "checked_columns": len(frame.columns),
        "failure_count": len(failures),
        "failures": failures[:200],
        "truncated": len(failures) > 200,
    }
