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


def _build_scope_refusal() -> str:
    return (
        "That is outside this bot's scope. It only answers within the declared Nietzsche themes "
        "already defined in the corpus: comfort and complacency, excuse-making, herd mentality, "
        "conformity, ressentiment, fear of struggle, self-overcoming, and becoming who you are."
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


def _build_passage_paragraph(chunk: dict, intro: str | None = None, max_length: int = 420) -> str:
    work = str(chunk.get("work") or "Nietzsche source").strip()
    section = str(chunk.get("section") or "").strip()
    text = str(chunk.get("display_text") or chunk.get("text") or "").strip()

    if not text:
        return ""

    source_line = f"{work}, {section}" if section else work
    clipped = _clip_text(text, max_length=max_length)

    if intro:
        return f"{intro} In {source_line}, the corpus points to this: {clipped}"

    return f"In {source_line}, the corpus points to this: {clipped}"


def _build_answer(
    user_message: str,
    retrieved_chunks: list[dict],
    matched_cards: list[dict],
) -> str:
    if not retrieved_chunks:
        return (
            "I do not have grounded Nietzsche material for that yet, "
            "so I will not fake an answer."
        )

    primary_chunk = retrieved_chunks[0]
    secondary_chunk = retrieved_chunks[1] if len(retrieved_chunks) > 1 else None

    top_card = matched_cards[0] if matched_cards else {}
    angle = str(top_card.get("nietzschean_angle", "")).strip()
    explanation = str(top_card.get("plain_explanation", "")).strip()

    parts: list[str] = []

    opening = angle or explanation
    if opening:
        parts.append(opening)

    primary_paragraph = _build_passage_paragraph(
        primary_chunk,
        intro="The strongest grounded support for that reading comes from the top retrieved passage.",
        max_length=420,
    )
    if primary_paragraph:
        parts.append(primary_paragraph)

    if secondary_chunk is not None:
        secondary_paragraph = _build_passage_paragraph(
            secondary_chunk,
            intro="A second passage strengthens the same line of interpretation.",
            max_length=280,
        )
        if secondary_paragraph:
            parts.append(secondary_paragraph)

    if explanation and explanation != opening:
        parts.append(explanation)

    return "\n\n".join(part for part in parts if part)


def generate_grounded_reply(message: str) -> ChatResponse:
    normalized_message = _normalize(message)

    if not _is_explicitly_in_scope(normalized_message):
        return ChatResponse(
            message=message,
            answer=_build_scope_refusal(),
            matched_card_ids=[],
            citations=[],
        )

    retrieved_chunks = search_retrieval_corpus(query=message, top_k=5)

    if not _retrieval_looks_in_scope(retrieved_chunks):
        return ChatResponse(
            message=message,
            answer=_build_scope_refusal(),
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
        text = str(item.get("display_text") or item.get("text", "")).strip()
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
        user_message=message,
        retrieved_chunks=retrieved_chunks,
        matched_cards=matched_cards,
    )

    return ChatResponse(
        message=message,
        answer=answer,
        matched_card_ids=matched_card_ids,
        citations=citations,
    )