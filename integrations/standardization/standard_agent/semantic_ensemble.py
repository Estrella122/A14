from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .ml_model import CharNGramCentroidModel


DEFAULT_EMBEDDING_WEIGHT = 0.20


class EmbeddingPrototypeIndex:
    def __init__(self, vectors: np.ndarray, scenarios: np.ndarray, labels: np.ndarray) -> None:
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self.scenarios = np.asarray(scenarios, dtype=str)
        self.labels = np.asarray(labels, dtype=str)

    @classmethod
    def build(cls, records: Iterable[dict[str, str]], encoder: Any, batch_size: int = 128) -> "EmbeddingPrototypeIndex":
        unique: dict[tuple[str, str, str], dict[str, str]] = {}
        for record in records:
            key = (record["text"], record["scenario_id"], record["standard_name"])
            unique[key] = record
        rows = list(unique.values())
        vectors = encoder.encode(
            [row["text"] for row in rows],
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return cls(
            np.asarray(vectors, dtype=np.float32),
            np.asarray([row["scenario_id"] for row in rows]),
            np.asarray([row["standard_name"] for row in rows]),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp.npz")
        np.savez_compressed(temporary, vectors=self.vectors, scenarios=self.scenarios, labels=self.labels)
        temporary.replace(path)

    @classmethod
    def load(cls, path: Path) -> "EmbeddingPrototypeIndex":
        payload = np.load(path, allow_pickle=False)
        return cls(payload["vectors"], payload["scenarios"], payload["labels"])

    def scores(self, query_vector: np.ndarray, scenario_id: str | None) -> dict[str, float]:
        mask = np.ones(len(self.labels), dtype=bool) if scenario_id is None else self.scenarios == scenario_id
        indices = np.flatnonzero(mask)
        if not len(indices):
            return {}
        similarities = self.vectors[indices] @ np.asarray(query_vector, dtype=np.float32)
        result: dict[str, float] = {}
        for label, score in zip(self.labels[indices], similarities, strict=True):
            result[str(label)] = max(result.get(str(label), -1.0), float(score))
        return result


@lru_cache(maxsize=2)
def load_embedding_encoder(path: Path) -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(str(path), local_files_only=True)


class HybridSemanticModel:
    model_type = "industrial_char_embedding_ensemble"

    def __init__(
        self,
        char_model: CharNGramCentroidModel,
        embedding_index: EmbeddingPrototypeIndex | None = None,
        encoder_path: Path | None = None,
        embedding_weight: float = DEFAULT_EMBEDDING_WEIGHT,
        encoder: Any | None = None,
    ) -> None:
        self.char_model = char_model
        self.embedding_index = embedding_index
        self.encoder_path = encoder_path
        self.embedding_weight = float(embedding_weight)
        self._encoder = encoder
        self._vector_cache: dict[str, np.ndarray] = {}
        self.metadata = dict(char_model.metadata)
        self.metadata.update(
            {
                "model_type": self.model_type,
                "char_weight": round(1.0 - self.embedding_weight, 3),
                "embedding_weight": round(self.embedding_weight, 3),
                "embedding_enabled": embedding_index is not None and encoder_path is not None,
                "embedding_prototypes": len(embedding_index.labels) if embedding_index is not None else 0,
            }
        )

    @classmethod
    def load(cls, model_path: Path, encoder_path: Path) -> "HybridSemanticModel":
        char_model = CharNGramCentroidModel.load(model_path)
        index_path = model_path.with_suffix(".embedding.npz")
        index = EmbeddingPrototypeIndex.load(index_path) if index_path.exists() and encoder_path.exists() else None
        return cls(char_model, index, encoder_path if index is not None else None)

    @property
    def encoder(self) -> Any | None:
        if self.embedding_index is None or self.encoder_path is None:
            return None
        if self._encoder is None:
            self._encoder = load_embedding_encoder(self.encoder_path)
        return self._encoder

    def _query_vector(self, text: str) -> np.ndarray | None:
        if text in self._vector_cache:
            return self._vector_cache[text]
        encoder = self.encoder
        if encoder is None:
            return None
        vector = encoder.encode([text], normalize_embeddings=True, show_progress_bar=False)[0]
        result = np.asarray(vector, dtype=np.float32)
        if len(self._vector_cache) >= 4096:
            self._vector_cache.pop(next(iter(self._vector_cache)))
        self._vector_cache[text] = result
        return result

    def prime(self, texts: Iterable[str], batch_size: int = 128) -> None:
        encoder = self.encoder
        missing = list(dict.fromkeys(str(text) for text in texts if str(text) not in self._vector_cache))
        if encoder is None or not missing:
            return
        vectors = encoder.encode(missing, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
        for text, vector in zip(missing, vectors, strict=True):
            self._vector_cache[text] = np.asarray(vector, dtype=np.float32)

    def predict(self, text: str, scenario_id: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        char_predictions = self.char_model.predict(text, scenario_id, limit=max(limit, len(self.char_model.centroids)))
        if (
            char_predictions
            and char_predictions[0]["standard_name"] == "__irrelevant__"
            and float(char_predictions[0]["score"]) >= float(self.char_model.metadata.get("accept_threshold", 0.30))
        ):
            return char_predictions[:limit]
        char_scores = {item["standard_name"]: float(item["score"]) for item in char_predictions}
        char_top_score = float(char_predictions[0]["score"]) if char_predictions else 0.0
        acceptance_cap = char_top_score if char_top_score < float(self.char_model.metadata.get("accept_threshold", 0.30)) else None
        vector = self._query_vector(str(text))
        if vector is None or self.embedding_index is None:
            return char_predictions[:limit]
        embedding_scores = self.embedding_index.scores(vector, scenario_id)
        labels = set(char_scores) | set(embedding_scores)
        candidates = []
        for label in labels:
            char_score = char_scores.get(label, 0.0)
            embedding_score = embedding_scores.get(label, 0.0)
            score = (1.0 - self.embedding_weight) * char_score + self.embedding_weight * embedding_score
            candidates.append(
                {
                    "scenario_id": scenario_id,
                    "standard_name": label,
                    "score": round(float(score), 4),
                    "char_score": round(char_score, 4),
                    "embedding_score": round(embedding_score, 4),
                }
            )
        candidates.sort(key=lambda item: item["score"], reverse=True)
        if acceptance_cap is not None and candidates and candidates[0]["score"] > acceptance_cap:
            scale = acceptance_cap / candidates[0]["score"]
            for item in candidates:
                item["score"] = round(float(item["score"] * scale), 4)
        return candidates[:limit]

    def save(self, path: Path) -> None:
        self.char_model.save(path)
        if self.embedding_index is not None:
            self.embedding_index.save(path.with_suffix(".embedding.npz"))
