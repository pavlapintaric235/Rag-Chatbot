from __future__ import annotations

from typing import Any

from app.services.card_lookup_service import load_all_cards
from app.services.retrieval_service import search_retrieval_corpus


def _tokenize(text: str) -> set[str]:
    import re

    token_pattern = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")
    return {
        token.lower()
        for token in token_pattern.findall(text)
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


def inspect_query(query: str, top_k: int = 5) -> dict[str, Any]:
    retrieved_chunks = search_retrieval_corpus(query=query, top_k=top_k)

    retrieved_source_ids = {
        str(item.get("source_id")).strip()
        for item in retrieved_chunks
        if item.get("source_id")
    }

    retrieved_signal_parts: list[str] = []

    for chunk in retrieved_chunks:
        retrieved_signal_parts.append(str(chunk.get("text", "")).strip())
        retrieved_signal_parts.append(str(chunk.get("work", "")).strip())
        retrieved_signal_parts.append(str(chunk.get("section", "")).strip())

        themes = chunk.get("themes", [])
        tags = chunk.get("tags", [])

        if isinstance(themes, list):
            retrieved_signal_parts.extend(str(item).strip() for item in themes if str(item).strip())

        if isinstance(tags, list):
            retrieved_signal_parts.extend(str(item).strip() for item in tags if str(item).strip())

    query_tokens = _tokenize(query)
    retrieved_signal_tokens = _tokenize(" ".join(retrieved_signal_parts))

    inspected_cards: list[dict[str, Any]] = []

    for card in load_all_cards():
        card_id = str(card.get("card_id", "")).strip()
        theme = str(card.get("theme", "")).strip()

        search_text = _build_card_search_text(card)
        card_tokens = _tokenize(search_text)

        card_source_ids = {
            str(source_id).strip()
            for source_id in card.get("source_ids", [])
            if str(source_id).strip()
        }

        query_overlap = sorted(query_tokens.intersection(card_tokens))
        retrieved_source_overlap = sorted(retrieved_source_ids.intersection(card_source_ids))
        retrieved_signal_overlap = sorted(
            retrieved_signal_tokens.intersection(
                _tokenize(" ".join(
                    [
                        theme,
                        " ".join(_normalize_string_list(card.get("tags", []))),
                        " ".join(_normalize_string_list(card.get("user_patterns", []))),
                    ]
                ))
            )
        )

        inspected_cards.append(
            {
                "card_id": card_id,
                "theme": theme,
                "query_overlap_tokens": query_overlap,
                "retrieved_source_overlap": retrieved_source_overlap,
                "retrieved_signal_overlap_tokens": retrieved_signal_overlap,
                "source_ids": sorted(card_source_ids),
                "tags": _normalize_string_list(card.get("tags", [])),
                "user_patterns": _normalize_string_list(card.get("user_patterns", [])),
            }
        )

    return {
        "query": query,
        "retrieved_chunks": retrieved_chunks,
        "inspected_cards": inspected_cards,
    }