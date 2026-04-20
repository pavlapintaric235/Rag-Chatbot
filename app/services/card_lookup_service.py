from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from app.core.config import settings


_TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")


def _tokenize(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_PATTERN.findall(text)
        if token.strip()
    }


def _normalize_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []

    normalized: list[str] = []

    for value in values:
        text = str(value).strip()
        if text:
            normalized.append(text)

    return normalized


@lru_cache(maxsize=1)
def load_all_cards() -> list[dict[str, Any]]:
    cards_dir = settings.cards_dir

    if not cards_dir.exists():
        return []

    cards: list[dict[str, Any]] = []

    for path in sorted(cards_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            cards.append(payload)

    return cards


def clear_card_cache() -> None:
    load_all_cards.cache_clear()


def _build_card_search_text(card: dict[str, Any]) -> str:
    parts: list[str] = []

    parts.append(str(card.get("theme", "")).strip())
    parts.append(str(card.get("nietzschean_angle", "")).strip())
    parts.append(str(card.get("plain_explanation", "")).strip())
    parts.append(str(card.get("sharp_reply_style", "")).strip())
    parts.append(str(card.get("card_text", "")).strip())

    parts.extend(_normalize_string_list(card.get("user_patterns", [])))
    parts.extend(_normalize_string_list(card.get("tags", [])))
    parts.extend(_normalize_string_list(card.get("primary_references", [])))
    parts.extend(_normalize_string_list(card.get("source_ids", [])))

    return " ".join(part for part in parts if part)


def _score_text_overlap(query_tokens: set[str], candidate_text: str) -> float:
    if not query_tokens:
        return 0.0

    candidate_tokens = _tokenize(candidate_text)
    if not candidate_tokens:
        return 0.0

    overlap = query_tokens.intersection(candidate_tokens)
    return float(len(overlap))


def _score_phrase_hits(card: dict[str, Any], query_lower: str) -> float:
    score = 0.0

    important_fields = [
        str(card.get("theme", "")).strip(),
        str(card.get("nietzschean_angle", "")).strip(),
    ]

    important_fields.extend(_normalize_string_list(card.get("user_patterns", [])))
    important_fields.extend(_normalize_string_list(card.get("tags", [])))

    for field in important_fields:
        field_lower = field.lower().strip()
        if not field_lower:
            continue

        if field_lower in query_lower:
            score += 4.0

    return score


def _score_source_overlap(
    card: dict[str, Any],
    retrieved_source_ids: set[str],
) -> float:
    card_source_ids = {
        str(source_id).strip()
        for source_id in card.get("source_ids", [])
        if str(source_id).strip()
    }

    if not card_source_ids or not retrieved_source_ids:
        return 0.0

    return float(len(card_source_ids.intersection(retrieved_source_ids))) * 6.0


def _score_retrieved_signal_overlap(
    card: dict[str, Any],
    retrieved_signal_tokens: set[str],
) -> float:
    if not retrieved_signal_tokens:
        return 0.0

    theme_tokens = _tokenize(str(card.get("theme", "")))
    tag_tokens = _tokenize(" ".join(_normalize_string_list(card.get("tags", []))))
    pattern_tokens = _tokenize(" ".join(_normalize_string_list(card.get("user_patterns", []))))

    score = 0.0
    score += float(len(theme_tokens.intersection(retrieved_signal_tokens))) * 3.0
    score += float(len(tag_tokens.intersection(retrieved_signal_tokens))) * 2.0
    score += float(len(pattern_tokens.intersection(retrieved_signal_tokens))) * 2.5

    return score


def _card_score(
    card: dict[str, Any],
    query_tokens: set[str],
    query_lower: str,
    retrieved_source_ids: set[str],
    retrieved_signal_tokens: set[str],
) -> float:
    search_text = _build_card_search_text(card)

    score = 0.0
    score += _score_text_overlap(query_tokens=query_tokens, candidate_text=search_text)
    score += _score_phrase_hits(card=card, query_lower=query_lower)
    score += _score_source_overlap(card=card, retrieved_source_ids=retrieved_source_ids)
    score += _score_retrieved_signal_overlap(
        card=card,
        retrieved_signal_tokens=retrieved_signal_tokens,
    )

    return score


def find_relevant_cards(
    query: str,
    retrieved_source_ids: set[str],
    retrieved_chunks: list[dict[str, Any]] | None = None,
    top_k: int = 2,
) -> list[dict[str, Any]]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    query_lower = normalized_query.lower()
    query_tokens = _tokenize(normalized_query)
    if not query_tokens:
        return []

    cards = load_all_cards()
    if not cards:
        return []

    retrieved_signal_parts: list[str] = []

    for chunk in retrieved_chunks or []:
        retrieved_signal_parts.append(str(chunk.get("text", "")).strip())
        retrieved_signal_parts.append(str(chunk.get("work", "")).strip())
        retrieved_signal_parts.append(str(chunk.get("section", "")).strip())

        themes = chunk.get("themes", [])
        tags = chunk.get("tags", [])

        if isinstance(themes, list):
            retrieved_signal_parts.extend(str(item).strip() for item in themes if str(item).strip())

        if isinstance(tags, list):
            retrieved_signal_parts.extend(str(item).strip() for item in tags if str(item).strip())

    retrieved_signal_tokens = _tokenize(" ".join(retrieved_signal_parts))

    scored_cards: list[tuple[float, dict[str, Any]]] = []

    for card in cards:
        score = _card_score(
            card=card,
            query_tokens=query_tokens,
            query_lower=query_lower,
            retrieved_source_ids=retrieved_source_ids,
            retrieved_signal_tokens=retrieved_signal_tokens,
        )
        if score <= 0:
            continue
        scored_cards.append((score, card))

    scored_cards.sort(
        key=lambda item: (item[0], str(item[1].get("card_id", ""))),
        reverse=True,
    )

    return [card for _, card in scored_cards[:top_k]]