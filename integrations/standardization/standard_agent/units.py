from __future__ import annotations

import re
from collections.abc import Callable

import pandas as pd


UNIT_ALIASES = {
    "℃": "degC",
    "°c": "degC",
    "degc": "degC",
    "c": "degC",
    "°f": "degF",
    "degf": "degF",
    "k": "K",
    "pa": "Pa",
    "kpa": "kPa",
    "mpa": "MPa",
    "nm3/h": "Nm3/h",
    "nm³/h": "Nm3/h",
    "m3/h": "m3/h",
    "m³/h": "m3/h",
    "mw": "MW",
    "rpm": "rpm",
    "a": "A",
    "hz": "Hz",
    "mg/l": "mg/L",
    "ph": "pH",
    "m/min": "m/min",
    "m/s": "m/s",
    "mm": "mm",
    "t/h": "t/h",
    "kg/h": "kg/h",
    "%": "percent",
    "percent": "percent",
}


CONVERSIONS: dict[tuple[str, str], tuple[str, Callable[[pd.Series], pd.Series]]] = {
    ("degF", "degC"): ("(x-32)*5/9", lambda series: (series - 32.0) * 5.0 / 9.0),
    ("K", "degC"): ("x-273.15", lambda series: series - 273.15),
    ("kPa", "Pa"): ("x*1000", lambda series: series * 1000.0),
    ("MPa", "Pa"): ("x*1000000", lambda series: series * 1_000_000.0),
    ("m/s", "m/min"): ("x*60", lambda series: series * 60.0),
    ("kg/h", "t/h"): ("x/1000", lambda series: series / 1000.0),
}


def normalize_unit(value: str | None) -> str | None:
    if not value:
        return None
    compact = str(value).strip().lower().replace(" ", "")
    return UNIT_ALIASES.get(compact, str(value).strip())


def split_header_unit(header: str) -> tuple[str, str | None]:
    text = str(header).strip()
    matches = list(re.finditer(r"[\[(（【]([^\])）】]+)[\])）】]", text))
    if matches:
        candidate = matches[-1].group(1).strip()
        unit = normalize_unit(candidate)
        if unit in set(UNIT_ALIASES.values()):
            base = (text[: matches[-1].start()] + text[matches[-1].end() :]).strip(" _-")
            return base, unit
    suffixes = sorted(UNIT_ALIASES, key=len, reverse=True)
    lowered = text.lower().replace(" ", "")
    for suffix in suffixes:
        normalized_suffix = suffix.lower().replace(" ", "")
        # A/B/C are common sensor-channel suffixes. Only an explicit uppercase
        # one-letter suffix is treated as a unit; lower snake-case names such as
        # upper_furnace_pressure_c keep their channel identity.
        if len(normalized_suffix) == 1 and not text.replace(" ", "").endswith("_" + suffix.upper()):
            continue
        if lowered.endswith("_" + normalized_suffix):
            return text[: -(len(suffix) + 1)], UNIT_ALIASES[suffix]
    return text, None


def conversion(source: str | None, target: str | None):
    if not source or not target or source == target:
        return None
    return CONVERSIONS.get((source, target))
