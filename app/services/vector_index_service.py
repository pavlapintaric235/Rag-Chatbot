from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.config import settings


def _normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []

    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)

    return normalized


def _build_searchable_text(item: dict[str, Any]) -> str:
    parts: list[str] = []

    parts.append(str(item.get("title", "")).strip())
    parts.append(str(item.get("work", "")).strip())
    parts.append(str(item.get("section", "")).strip())
    parts.append(str(item.get("mode", "")).strip())
    parts.append(str(item.get("tone", "")).strip())
    parts.append(" ".join(_normalize_list(item.get("themes", []))))
    parts.append(" ".join(_normalize_list(item.get("tags", []))))
    parts.append(str(item.get("text", "")).strip())

    return " ".join(part for part in parts if part)


def build_vector_index() -> dict[str, Path | int]:
    corpus_path = settings.retrieval_corpus_path
    index_dir = settings.vector_store_dir
    metadata_path = settings.vector_index_metadata_path
    matrix_path = settings.vector_index_matrix_path
    vectorizer_path = settings.vectorizer_path

    if not corpus_path.exists():
        raise FileNotFoundError(f"Retrieval corpus not found: {corpus_path}")

    payload = json.loads(corpus_path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Retrieval corpus must be a JSON object.")

    items = payload.get("items")

    if not isinstance(items, list) or not items:
        raise ValueError("Retrieval corpus must contain a non-empty 'items' list.")

    searchable_texts: list[str] = []
    normalized_items: list[dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each retrieval corpus item must be an object.")

        searchable_text = _build_searchable_text(item).strip()
        if not searchable_text:
            continue

        searchable_texts.append(searchable_text)
        normalized_items.append(item)

    if not searchable_texts:
        raise ValueError("No searchable texts were built from retrieval corpus items.")

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )
    matrix = vectorizer.fit_transform(searchable_texts)

    index_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(vectorizer, vectorizer_path)
    joblib.dump(matrix, matrix_path)

    metadata_payload = {
        "item_count": len(normalized_items),
        "items": normalized_items,
    }
    metadata_path.write_text(
        json.dumps(metadata_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "vectorizer_path": vectorizer_path,
        "matrix_path": matrix_path,
        "metadata_path": metadata_path,
        "item_count": len(normalized_items),
    }