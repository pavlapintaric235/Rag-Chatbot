from __future__ import annotations

from app.models.chat import ChatCitation, ChatResponse
from app.services.card_lookup_service import find_relevant_cards
from app.services.retrieval_service import search_retrieval_corpus


def _clip_text(text: str, max_length: int = 280) -> str:
    normalized = " ".join(text.split()).strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def _build_card_driven_opening(matched_cards: list[dict], user_message: str) -> str:
    if not matched_cards:
        return (
            "Your message points to a real psychological pattern, not just a passing mood. "
            "So the first job is to name the pattern honestly and refuse the flattering lie inside it."
        )

    top_card = matched_cards[0]

    theme = str(top_card.get("theme", "")).strip()
    angle = str(top_card.get("nietzschean_angle", "")).strip()
    explanation = str(top_card.get("plain_explanation", "")).strip()

    parts: list[str] = []

    if theme:
        parts.append(f"Primary pattern detected: {theme}.")

    if angle:
        parts.append(angle)

    if explanation:
        parts.append(explanation)

    return "\n\n".join(parts)


def _build_action_turn(matched_cards: list[dict]) -> str:
    if not matched_cards:
        return (
            "The move now is to stop turning the pattern into identity. "
            "Interrupt it in action, not just in analysis."
        )

    top_card = matched_cards[0]
    sharp_reply_style = str(top_card.get("sharp_reply_style", "")).strip()

    if sharp_reply_style:
        return sharp_reply_style

    return (
        "The move now is to stop turning the pattern into identity. "
        "Interrupt it in action, not just in analysis."
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


def _pick_secondary_support_chunk(retrieved_chunks: list[dict]) -> dict | None:
    if not retrieved_chunks:
        return None

    primary_source_id = str(retrieved_chunks[0].get("source_id") or "").strip()

    for chunk in retrieved_chunks[1:]:
        source_id = str(chunk.get("source_id") or "").strip()
        if source_id and source_id != primary_source_id:
            return chunk

    if len(retrieved_chunks) >= 2:
        return retrieved_chunks[1]

    return None


def _build_source_bridge(retrieved_chunks: list[dict]) -> str:
    if not retrieved_chunks:
        return (
            "I do not have grounded Nietzsche material for that yet. "
            "Your current corpus did not return a relevant passage, so I will not fake one."
        )

    primary_chunk = retrieved_chunks[0]
    primary_text = str(
        primary_chunk.get("display_text")
        or primary_chunk.get("text", "")
    ).strip()
    primary_work = str(primary_chunk.get("work") or "Nietzsche source").strip()
    primary_section = str(primary_chunk.get("section") or "").strip()

    parts: list[str] = []

    if primary_section:
        parts.append(
            f"The strongest supporting passage I found is from {primary_work}, section {primary_section}."
        )
    else:
        parts.append(
            f"The strongest supporting passage I found is from {primary_work}."
        )

    parts.append(
        f"Grounded passage: {_clip_text(primary_text, max_length=320)}"
    )

    secondary_chunk = _pick_secondary_support_chunk(retrieved_chunks)
    if secondary_chunk is not None:
        secondary_text = str(
            secondary_chunk.get("display_text")
            or secondary_chunk.get("text", "")
        ).strip()
        secondary_work = str(secondary_chunk.get("work") or "Nietzsche source").strip()
        secondary_section = str(secondary_chunk.get("section") or "").strip()

        if secondary_text:
            if secondary_section:
                parts.append(
                    f"A second supporting passage comes from {secondary_work}, section {secondary_section}: "
                    f"{_clip_text(secondary_text, max_length=220)}"
                )
            else:
                parts.append(
                    f"A second supporting passage comes from {secondary_work}: "
                    f"{_clip_text(secondary_text, max_length=220)}"
                )

    return "\n\n".join(parts)


def _build_answer(
    user_message: str,
    retrieved_chunks: list[dict],
    matched_cards: list[dict],
) -> str:
    if not retrieved_chunks:
        return (
            "I do not have grounded Nietzsche material for that yet. "
            "Your current corpus did not return a relevant passage, so I will not fake one."
        )

    opening = _build_card_driven_opening(
        matched_cards=matched_cards,
        user_message=user_message,
    )
    source_bridge = _build_source_bridge(retrieved_chunks=retrieved_chunks)
    action_turn = _build_action_turn(matched_cards=matched_cards)

    return "\n\n".join([opening, source_bridge, action_turn])


def generate_grounded_reply(message: str) -> ChatResponse:
    retrieved_chunks = search_retrieval_corpus(query=message, top_k=5)

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