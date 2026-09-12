from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


CONCEPT_PATTERNS = (
    ("direction_in", r"influent|inlet|入口|进口|进水|进料|入炉|入口侧"),
    ("direction_out", r"effluent|outlet|出口|出口侧|出水|出料|排出"),
    ("direction_upper", r"\bupper\b|上部|上段|上层|上压差"),
    ("direction_lower", r"\blower\b|下部|下段|下层|下压差"),
    ("direction_hot", r"\bhot\b|热风|热端|热侧"),
    ("direction_cold", r"\bcold\b|冷风|冷端|冷侧"),
    ("order_primary", r"primary|一次|\bpa\b"),
    ("order_secondary", r"secondary|二次|\bsa\b"),
    ("variant_a", r"(?<![a-z])a(?![a-z])|[_\-\s]a(?:[_\-\s]|$)|\ba线\b|温度a|压力a"),
    ("variant_b", r"(?<![a-z])b(?![a-z])|[_\-\s]b(?:[_\-\s]|$)|\bb线\b|温度b|压力b"),
    ("zone_1", r"zone[_\- ]?1|一区|一段|预热段|炉温1"),
    ("zone_2", r"zone[_\- ]?2|二区|二段|加热段|炉温2"),
    ("zone_3", r"zone[_\- ]?3|三区|三段|均热段|炉温3"),
    ("position_top", r"\btop\b|塔顶|顶部"),
    ("position_bottom", r"\bbottom\b|塔底|底部"),
    ("material_rawmeal", r"raw[_\- ]?meal|生料|raw[_\- ]?feed"),
    ("material_coal", r"coal|煤粉|煤量|喂煤"),
    ("kind_timestamp", r"timestamp|date[_\- ]?time|采集时间|时间戳"),
    ("measure_temp", r"temp(?:erature)?|\btt\b|温度|炉温"),
    ("measure_flow", r"flow|流量|风量"),
    ("measure_pressure", r"pressure|\bpt\b|压力|压强"),
    ("measure_pressure_drop", r"pressure[_\- ]?difference|pressure[_\- ]?drop|压差"),
    ("measure_level", r"level|液位|料位"),
    ("direction_lagging", r"lagging|滞后"),
    ("direction_leading", r"leading|超前"),
    ("measure_reactive_energy", r"reactive|无功"),
    ("measure_power_factor", r"power[_\- ]?factor|功率因数"),
    ("measure_energy_usage", r"usage[_\- ]?kwh|energy[_\- ]?consumption|用电量|能耗"),
    ("measure_carbon", r"co2|carbon|二氧化碳"),
    ("measure_frequency", r"frequency|频率|转速"),
    ("chem_ammonia", r"ammonia|nh3[_\-]?n|氨氮"),
    ("chem_cod", r"\bcod\b|化学需氧量"),
)

ORDINAL_PATTERN = re.compile(
    r"(?:zone|temp|temperature|pressure|level|flow|tp|炉温|温度|压力|压差|液位|流量|周边|炉顶)[_\-\s#]*(\d{1,2})"
    r"|(\d{1,2})\s*(?:号)?(?:区|段|层|点|通道|周边|炉顶|温度|压力|压差|液位|流量)"
)

LETTER_VARIANT_PATTERN = re.compile(
    r"(?:^|[_\-\s#.]|[温压])([ab])(?:$|[_\-\s#.]|线|相|侧|温度|压力)|(?:温度|压力|流量)([ab])",
    re.I,
)


def semantic_core(text: str) -> str:
    value = str(text).lower()
    value = re.sub(r"(?:dcs|plc|sis|rtu|hmi|apc)[_.#\-]*\d*", " ", value)
    value = re.sub(r"(?:装置\d+|[ab]线|\d+号机组|二期|主控|现场)", " ", value)
    value = re.sub(r"(?:测点(?:[_.#\-]*\d+)?|ch[_.#\-]*\d+)", " ", value)
    tokens = re.split(r"[^0-9a-z\u4e00-\u9fff]+", value)
    noise = {"pv", "sp", "ai", "raw", "value", "meas"}
    meaningful = [token for token in tokens if token and token not in noise and not token.isdigit()]
    return "".join(meaningful)


def text_features(text: str) -> Counter[str]:
    compact = semantic_core(text)
    features: Counter[str] = Counter()
    for size in (1, 2, 3):
        for index in range(max(len(compact) - size + 1, 0)):
            features[f"{size}:{compact[index:index + size]}"] += 1
    concepts = []
    lowered = str(text).lower().replace("_", " ")
    for concept, pattern in CONCEPT_PATTERNS:
        if re.search(pattern, lowered):
            concepts.append(concept)
            features[f"concept:{concept}"] += 4
    for match in ORDINAL_PATTERN.finditer(lowered):
        number = next((group for group in match.groups() if group), None)
        if number is None:
            continue
        normalized = str(int(number))
        concepts.append(f"ordinal_{normalized}")
        features[f"ordinal:{normalized}"] += 6
        for concept in concepts:
            if concept.startswith("measure_") or concept.startswith("position_") or concept.startswith("direction_"):
                features[f"ordinal_pair:{concept}+{normalized}"] += 3
    for match in LETTER_VARIANT_PATTERN.finditer(lowered):
        letter = next((group for group in match.groups() if group), "").lower()
        if letter:
            concepts.append(f"variant_{letter}")
            features[f"variant:{letter}"] += 5
            for concept in concepts:
                if concept.startswith("measure_") or concept.startswith("position_"):
                    features[f"variant_pair:{concept}+{letter}"] += 3
    for left in concepts:
        for right in concepts:
            if left < right:
                features[f"concept_pair:{left}+{right}"] += 2
    return features


class CharNGramCentroidModel:
    model_type = "char_ngram_tfidf_centroid"

    def __init__(self) -> None:
        self.idf: dict[str, float] = {}
        self.centroids: dict[str, dict[str, float]] = {}
        self.prototypes: dict[str, list[dict[str, float]]] = {}
        self.metadata: dict[str, Any] = {}

    @staticmethod
    def label(scenario_id: str, standard_name: str) -> str:
        return f"{scenario_id}::{standard_name}"

    def fit(self, records: Iterable[dict[str, str]], max_features: int = 6000) -> "CharNGramCentroidModel":
        documents = []
        document_frequency: Counter[str] = Counter()
        for record in records:
            features = text_features(record["text"])
            label = self.label(record["scenario_id"], record["standard_name"])
            documents.append((label, semantic_core(record["text"]), features))
            document_frequency.update(features.keys())
        if not documents:
            raise ValueError("训练数据为空。")
        keep = {key for key, _ in document_frequency.most_common(max_features)}
        total = len(documents)
        self.idf = {key: math.log((1 + total) / (1 + document_frequency[key])) + 1 for key in keep}
        sums: dict[str, Counter[str]] = defaultdict(Counter)
        counts: Counter[str] = Counter()
        prototype_vectors: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
        for label, core, raw in documents:
            vector = self._vector(raw)
            norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
            normalized = {key: value / norm for key, value in vector.items()}
            sums[label].update(normalized)
            counts[label] += 1
            if core and core not in prototype_vectors[label]:
                prototype_vectors[label][core] = normalized
        self.centroids = {}
        for label, values in sums.items():
            average = {key: value / counts[label] for key, value in values.items()}
            norm = math.sqrt(sum(value * value for value in average.values())) or 1.0
            self.centroids[label] = {key: value / norm for key, value in average.items()}
        self.prototypes = {label: list(items.values()) for label, items in prototype_vectors.items()}
        self.metadata = {"training_samples": total, "labels": len(self.centroids), "features": len(self.idf), "prototypes": sum(len(items) for items in self.prototypes.values()), "accept_threshold": 0.30}
        return self

    def _vector(self, raw: Counter[str]) -> dict[str, float]:
        maximum = max(raw.values(), default=1)
        return {key: (0.5 + 0.5 * value / maximum) * self.idf[key] for key, value in raw.items() if key in self.idf}

    def predict(self, text: str, scenario_id: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        vector = self._vector(text_features(text))
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        vector = {key: value / norm for key, value in vector.items()}
        candidates = []
        prefix = f"{scenario_id}::" if scenario_id else None
        for label, centroid in self.centroids.items():
            if prefix and not label.startswith(prefix):
                continue
            centroid_score = sum(value * centroid.get(key, 0.0) for key, value in vector.items())
            prototype_score = max(
                (sum(value * prototype.get(key, 0.0) for key, value in vector.items()) for prototype in self.prototypes.get(label, [])),
                default=0.0,
            )
            score = max(centroid_score, prototype_score)
            scenario, standard = label.split("::", 1)
            candidates.append({"scenario_id": scenario, "standard_name": standard, "score": round(float(score), 4)})
        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:limit]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"model_type": self.model_type, "metadata": self.metadata, "idf": self.idf, "centroids": self.centroids, "prototypes": self.prototypes}
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "CharNGramCentroidModel":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("model_type") != cls.model_type:
            raise ValueError("字段语义模型类型不兼容。")
        model = cls()
        model.metadata = payload["metadata"]
        model.idf = {key: float(value) for key, value in payload["idf"].items()}
        model.centroids = {label: {key: float(value) for key, value in vector.items()} for label, vector in payload["centroids"].items()}
        model.prototypes = {label: [{key: float(value) for key, value in vector.items()} for vector in vectors] for label, vectors in payload.get("prototypes", {}).items()}
        return model
