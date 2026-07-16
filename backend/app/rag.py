from __future__ import annotations

import importlib.util
import math
import os
from threading import Lock
from typing import Iterable


DEFAULT_VECTOR_MODEL = "BAAI/bge-small-zh-v1.5"


class LocalVectorIndex:
    """Small in-memory vector index with a keyword-only fallback."""

    def __init__(self, model_name: str = DEFAULT_VECTOR_MODEL) -> None:
        self.model_name = model_name
        self._documents: list[str] = []
        self._vectors: list[list[float]] = []
        self._model = None
        self._attempted = False
        self._error = ""
        self._lock = Lock()

    def configure(self, documents: Iterable[str]) -> None:
        with self._lock:
            self._documents = [str(document) for document in documents]
            self._vectors = []
            self._attempted = False
            self._error = ""

    def search(self, query: str) -> dict[int, float]:
        if not query.strip() or not self._ensure_static_index():
            return {}

        query_vector = self._embed_query(query)
        if not query_vector:
            return {}
        return {
            index: _cosine_similarity(query_vector, vector)
            for index, vector in enumerate(self._vectors)
        }

    def rank_texts(self, query: str, documents: list[str]) -> dict[int, float]:
        if not query.strip() or not documents or not self._ensure_model():
            return {}

        try:
            query_vector = self._embed_query(query)
            passage_vectors = [
                _normalize(vector)
                for vector in self._model.passage_embed(documents)
            ]
        except Exception as exc:  # The keyword path must survive model/runtime failures.
            self._error = f"{type(exc).__name__}: {exc}"
            return {}

        return {
            index: _cosine_similarity(query_vector, vector)
            for index, vector in enumerate(passage_vectors)
        }

    def status(self) -> dict[str, object]:
        dependency_available = importlib.util.find_spec("fastembed") is not None
        return {
            "mode": "hybrid" if self._vectors else "keyword",
            "model_name": self.model_name,
            "dependency_available": dependency_available,
            "initialized": bool(self._vectors),
            "document_count": len(self._documents),
            "error": self._error,
        }

    def _ensure_static_index(self) -> bool:
        if self._vectors:
            return True
        if not self._ensure_model():
            return False

        with self._lock:
            if self._vectors:
                return True
            try:
                self._vectors = [
                    _normalize(vector)
                    for vector in self._model.passage_embed(self._documents)
                ]
            except Exception as exc:
                self._error = f"{type(exc).__name__}: {exc}"
                self._vectors = []
                return False
        return bool(self._vectors)

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        if self._attempted:
            return False

        with self._lock:
            if self._model is not None:
                return True
            if self._attempted:
                return False
            self._attempted = True

            if os.getenv("AGENT_TOWN_DISABLE_VECTOR_RAG", "").lower() in {"1", "true", "yes"}:
                self._error = "向量检索已由 AGENT_TOWN_DISABLE_VECTOR_RAG 禁用。"
                return False
            if importlib.util.find_spec("fastembed") is None:
                self._error = "未安装 fastembed，已使用关键词检索。"
                return False

            try:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=self.model_name, threads=2)
            except Exception as exc:
                self._error = f"{type(exc).__name__}: {exc}"
                self._model = None
                return False
        return True

    def _embed_query(self, query: str) -> list[float]:
        try:
            vector = next(iter(self._model.query_embed([query])))
        except Exception as exc:
            self._error = f"{type(exc).__name__}: {exc}"
            return []
        return _normalize(vector)


def _normalize(vector: Iterable[float]) -> list[float]:
    values = [float(value) for value in vector]
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude <= 0:
        return values
    return [value / magnitude for value in values]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    return sum(left_value * right_value for left_value, right_value in zip(left, right))


HYBRID_INDEX = LocalVectorIndex()
