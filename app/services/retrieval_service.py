from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from typing import Any

import joblib
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings


_TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "here",
    "hers",
    "him",
    "his",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "me",
    "more",
    "most",
    "my",
    "of",
    "on",
    "or",
    "our",
    "ours",
    "she",
    "so",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "to",
    "too",
    "us",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "you",
    "your",
    "yours",
}


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []

    for raw_token in _TOKEN_PATTERN.findall(text):
        token = raw_token.lower().strip("'").strip()

        if not token:
            continue

        if len(token) < 3:
            continue

        if token in _STOPWORDS:
            continue

        tokens.append(token)

    return tokens


@lru_cache(maxsize=1)
def _load_retrieval_corpus() -> dict[str, Any]:
    corpus_path = settings.retrieval_corpus_path

    if not corpus_path.exists():
        raise FileNotFoundError(
            f"Retrieval corpus not found: {corpus_path}"
        )

    payload = json.loads(corpus_path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Retrieval corpus must be a JSON object.")

    items = payload.get("items")

    if not isinstance(items, list):
        raise ValueError("Retrieval corpus 'items' must be a list.")

    return payload


@lru_cache(maxsize=1)
def _load_vector_index() -> tuple[Any, Any, list[dict[str, Any]]]:
    vectorizer_path = settings.vectorizer_path
    matrix_path = settings.vector_index_matrix_path
    metadata_path = settings.vector_index_metadata_path

    if not vectorizer_path.exists():
        raise FileNotFoundError(f"Vectorizer not found: {vectorizer_path}")
    if not matrix_path.exists():
        raise FileNotFoundError(f"Vector matrix not found: {matrix_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Vector metadata not found: {metadata_path}")

    vectorizer = joblib.load(vectorizer_path)
    matrix = joblib.load(matrix_path)

    metadata_payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    items = metadata_payload.get("items")

    if not isinstance(items, list):
        raise ValueError("Vector metadata 'items' must be a list.")

    return vectorizer, matrix, items


def clear_retrieval_corpus_cache() -> None:
    _load_retrieval_corpus.cache_clear()
    _load_vector_index.cache_clear()


def _normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []

    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)

    return normalized


def _build_document_frequency(items: list[dict[str, Any]]) -> Counter[str]:
    document_frequency: Counter[str] = Counter()

    for item in items:
        searchable_text = _build_searchable_text(item)
        unique_tokens = set(_tokenize(searchable_text))
        document_frequency.update(unique_tokens)

    return document_frequency


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


def _field_boost_score(query_tokens: list[str], item: dict[str, Any]) -> float:
    score = 0.0

    title_tokens = set(_tokenize(str(item.get("title", ""))))
    work_tokens = set(_tokenize(str(item.get("work", ""))))
    section_tokens = set(_tokenize(str(item.get("section", ""))))
    theme_tokens = set(_tokenize(" ".join(_normalize_list(item.get("themes", [])))))
    tag_tokens = set(_tokenize(" ".join(_normalize_list(item.get("tags", [])))))
    text_tokens = set(_tokenize(str(item.get("text", ""))))

    for token in query_tokens:
        if token in theme_tokens:
            score += 4.0
        if token in tag_tokens:
            score += 3.0
        if token in title_tokens:
            score += 2.5
        if token in section_tokens:
            score += 1.5
        if token in work_tokens:
            score += 1.0
        if token in text_tokens:
            score += 0.5

    return score


def _keyword_score_chunk(
    query_tokens: list[str],
    item: dict[str, Any],
    document_frequency: Counter[str],
    total_documents: int,
) -> float:
    if not query_tokens:
        return 0.0

    searchable_text = _build_searchable_text(item)
    chunk_tokens = _tokenize(searchable_text)

    if not chunk_tokens:
        return 0.0

    term_counts = Counter(chunk_tokens)
    chunk_length = len(chunk_tokens)

    score = 0.0

    for token in query_tokens:
        tf = term_counts.get(token, 0)
        if tf == 0:
            continue

        df = document_frequency.get(token, 0)
        idf = math.log((1 + total_documents) / (1 + df)) + 1.0
        normalized_tf = tf / chunk_length
        score += normalized_tf * idf

    score += _field_boost_score(query_tokens=query_tokens, item=item)

    overlap_count = len(set(query_tokens).intersection(set(chunk_tokens)))
    score += overlap_count * 1.25

    return score


def _apply_source_diversity(
    scored_results: list[dict[str, Any]],
    top_k: int,
    max_per_source: int = 2,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}

    for result in scored_results:
        source_id = str(result.get("source_id") or "").strip()
        current_count = source_counts.get(source_id, 0)

        if source_id and current_count >= max_per_source:
            continue

        selected.append(result)

        if source_id:
            source_counts[source_id] = current_count + 1

        if len(selected) >= top_k:
            return selected

    if len(selected) < top_k:
        seen_chunk_ids = {
            str(item.get("chunk_id") or "").strip()
            for item in selected
        }

        for result in scored_results:
            chunk_id = str(result.get("chunk_id") or "").strip()
            if chunk_id in seen_chunk_ids:
                continue

            selected.append(result)
            seen_chunk_ids.add(chunk_id)

            if len(selected) >= top_k:
                break

    return selected[:top_k]


def search_retrieval_corpus(
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    normalized_query = query.strip()

    if not normalized_query:
        return []

    query_tokens = _tokenize(normalized_query)
    if not query_tokens:
        return []

    try:
        vectorizer, matrix, items = _load_vector_index()
        query_vector = vectorizer.transform([normalized_query])
        similarities = cosine_similarity(query_vector, matrix).flatten()

        corpus = _load_retrieval_corpus()
        fallback_items = corpus.get("items", [])
        document_frequency = _build_document_frequency(fallback_items)
        total_documents = len(fallback_items) if fallback_items else 1

        scored_results: list[dict[str, Any]] = []

        for index, item in enumerate(items):
            text = str(item.get("text", "")).strip()
            display_text = str(item.get("display_text") or text).strip()

            vector_score = float(similarities[index])
            keyword_score = _keyword_score_chunk(
                query_tokens=query_tokens,
                item=item,
                document_frequency=document_frequency,
                total_documents=total_documents,
            )

            combined_score = (vector_score * 100.0) + keyword_score

            if combined_score <= 0:
                continue

            result = {
                "chunk_id": item.get("chunk_id"),
                "source_id": item.get("source_id"),
                "title": item.get("title"),
                "work": item.get("work"),
                "section": item.get("section"),
                "themes": item.get("themes", []),
                "mode": item.get("mode"),
                "tone": item.get("tone"),
                "tags": item.get("tags", []),
                "text": text,
                "display_text": display_text,
                "score": round(combined_score, 8),
                "vector_score": round(vector_score, 8),
                "keyword_score": round(keyword_score, 8),
            }
            scored_results.append(result)

        scored_results.sort(
            key=lambda row: (
                row["score"],
                row["source_id"] or "",
                row["chunk_id"] or "",
            ),
            reverse=True,
        )

        return _apply_source_diversity(scored_results=scored_results, top_k=top_k)

    except FileNotFoundError:
        corpus = _load_retrieval_corpus()
        items = corpus.get("items", [])

        if not items:
            return []

        document_frequency = _build_document_frequency(items)
        total_documents = len(items)

        scored_results: list[dict[str, Any]] = []

        for item in items:
            text = str(item.get("text", "")).strip()
            display_text = str(item.get("display_text") or text).strip()

            score = _keyword_score_chunk(
                query_tokens=query_tokens,
                item=item,
                document_frequency=document_frequency,
                total_documents=total_documents,
            )

            if score <= 0:
                continue

            result = {
                "chunk_id": item.get("chunk_id"),
                "source_id": item.get("source_id"),
                "title": item.get("title"),
                "work": item.get("work"),
                "section": item.get("section"),
                "themes": item.get("themes", []),
                "mode": item.get("mode"),
                "tone": item.get("tone"),
                "tags": item.get("tags", []),
                "text": text,
                "display_text": display_text,
                "score": round(score, 8),
            }
            scored_results.append(result)

        scored_results.sort(
            key=lambda row: (row["score"], row["source_id"] or "", row["chunk_id"] or ""),
            reverse=True,
        )

        return _apply_source_diversity(scored_results=scored_results, top_k=top_k)