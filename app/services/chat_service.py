from __future__ import annotations

from app.models.chat import ChatCitation, ChatResponse
from app.services.card_lookup_service import find_relevant_cards
from app.services.retrieval_service import search_retrieval_corpus

_ALLOWED_TOPIC_TERMS: tuple[str, ...] = (
    "comfort",
    "complacency",
    "easy life",
    "safety",
    "security",
    "comfort zone",
    "weakness",
    "excuse",
    "excuses",
    "rationalize",
    "rationalise",
    "self-deception",
    "self deception",
    "avoidance",
    "avoid",
    "fear of struggle",
    "struggle",
    "discipline",
    "self-overcoming",
    "self overcoming",
    "becoming who you are",
    "become who i am",
    "become who you are",
    "herd",
    "herd mentality",
    "conformity",
    "conformism",
    "resentment",
    "ressentiment",
    "last man",
    "greatness",
    "mediocrity",
    "drift",
    "comfort-seeking",
    "comfort seeking",
)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split()).strip()


def _clip_text(text: str, max_length: int = 220) -> str:
    normalized = " ".join(text.split()).strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def _is_explicitly_in_scope(message: str) -> bool:
    normalized = _normalize(message)
    return any(term in normalized for term in _ALLOWED_TOPIC_TERMS)


def _retrieval_looks_in_scope(retrieved_chunks: list[dict]) -> bool:
    if not retrieved_chunks:
        return False

    for chunk in retrieved_chunks:
        themes = [str(item).strip().lower() for item in chunk.get("themes", []) if str(item).strip()]
        tags = [str(item).strip().lower() for item in chunk.get("tags", []) if str(item).strip()]
        haystack = " | ".join(themes + tags)

        if not haystack:
            continue

        if any(term in haystack for term in _ALLOWED_TOPIC_TERMS):
            return True

    return False


def _build_scope_refusal(message: str) -> str:
    return (
        "That is outside this bot's scope. It only answers within the Nietzsche themes "
        "already defined in the corpus: comfort and complacency, excuse-making, herd mentality, "
        "conformity, ressentiment, fear of struggle, self-overcoming, and becoming who you are. "
        "Ask within those themes and I will answer from the corpus."
    )


def _select_diverse_citation_chunks(
    retrieved_chunks: list[dict],
    max_citations: int = 3,
) -> list[dict]:
    if not retrieved_chunks:
        return []

    selected: list[dict] = []
    seen_sources: set[str] = set()

    for chunk in retrieved_chunks:
        source_id = str(chunk.get("source_id") or "").strip()

        if source_id and source_id in seen_sources:
            continue

        selected.append(chunk)

        if source_id:
            seen_sources.add(source_id)

        if len(selected) >= max_citations:
            return selected

    if len(selected) < max_citations:
        seen_chunk_ids = {
            str(item.get("chunk_id") or "").strip()
            for item in selected
        }

        for chunk in retrieved_chunks:
            chunk_id = str(chunk.get("chunk_id") or "").strip()

            if chunk_id in seen_chunk_ids:
                continue

            selected.append(chunk)
            seen_chunk_ids.add(chunk_id)

            if len(selected) >= max_citations:
                break

    return selected[:max_citations]


def _build_answer(
    retrieved_chunks: list[dict],
    matched_cards: list[dict],
) -> str:
    if matched_cards:
        top_card = matched_cards[0]

        angle = str(top_card.get("nietzschean_angle", "")).strip()
        explanation = str(top_card.get("plain_explanation", "")).strip()
        action_turn = str(top_card.get("sharp_reply_style", "")).strip()

        parts: list[str] = []

        first_paragraph = angle or explanation
        if first_paragraph:
            parts.append(first_paragraph)

        if explanation and explanation != first_paragraph:
            parts.append(explanation)

        if action_turn:
            parts.append(action_turn)

        cleaned_parts = [part for part in parts if part]
        if cleaned_parts:
            return "\n\n".join(cleaned_parts[:3])

    if retrieved_chunks:
        top_chunk = retrieved_chunks[0]
        top_text = str(
            top_chunk.get("display_text")
            or top_chunk.get("text", "")
        ).strip()

        if top_text:
            return (
                "The corpus does point to a relevant pattern here. "
                f"{_clip_text(top_text, max_length=320)}"
            )

    return (
        "I do not have grounded Nietzsche material for that yet, "
        "so I will not fake an answer."
    )


def generate_grounded_reply(message: str) -> ChatResponse:
    normalized_message = _normalize(message)

    if not _is_explicitly_in_scope(normalized_message):
        return ChatResponse(
            message=message,
            answer=_build_scope_refusal(message),
            matched_card_ids=[],
            citations=[],
        )

    retrieved_chunks = search_retrieval_corpus(query=message, top_k=5)

    if not _retrieval_looks_in_scope(retrieved_chunks):
        return ChatResponse(
            message=message,
            answer=_build_scope_refusal(message),
            matched_card_ids=[],
            citations=[],
        )

    retrieved_source_ids = {
        str(item.get("source_id")).strip()
        for item in retrieved_chunks
        if item.get("source_id")
    }

    matched_cards = find_relevant_cards(
        query=message,
        retrieved_source_ids=retrieved_source_ids,
        retrieved_chunks=retrieved_chunks,
        top_k=2,
    )

    citations: list[ChatCitation] = []
    citation_chunks = _select_diverse_citation_chunks(
        retrieved_chunks=retrieved_chunks,
        max_citations=3,
    )

    for item in citation_chunks:
        text = str(
            item.get("display_text")
            or item.get("text", "")
        ).strip()
        if not text:
            continue

        citations.append(
            ChatCitation(
                source_id=item.get("source_id"),
                chunk_id=item.get("chunk_id"),
                work=item.get("work"),
                section=item.get("section"),
                score=float(item.get("score", 0.0)),
                text_excerpt=_clip_text(text, max_length=220),
            )
        )

    matched_card_ids = [
        str(card.get("card_id")).strip()
        for card in matched_cards
        if str(card.get("card_id", "")).strip()
    ]

    answer = _build_answer(
        retrieved_chunks=retrieved_chunks,
        matched_cards=matched_cards,
    )

    return ChatResponse(
        message=message,
        answer=answer,
        matched_card_ids=matched_card_ids,
        citations=citations,
    )