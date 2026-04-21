from __future__ import annotations

import re
from collections import Counter

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

_STOPWORDS: set[str] = {
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
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "me",
    "my",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "them",
    "then",
    "they",
    "this",
    "to",
    "what",
    "when",
    "why",
    "with",
    "you",
    "your",
}

_METADATA_CUTOFF_PATTERNS: tuple[str, ...] = (
    r"\bUSEFUL USER MESSAGES THIS HELPS WITH\b.*",
    r"\bUSEFUL USER MESSAGES\b.*",
    r"\bTHIS HELPS WITH\b.*",
    r"\bWHAT HE IS ATTACKING\b.*",
    r"\bWHAT HE IS NOT SAYING\b.*",
    r"\bAVOID\b.*",
    r"\bDO NOT\b.*",
    r"\bMISREADING RISK\b.*",
    r"\bSAFE USE NOTE\b.*",
    r"\bPRIMARY REFERENCES\b.*",
    r"\bUSER MESSAGE EXAMPLE\b.*",
    r"\bUSER PATTERNS\b.*",
    r"\bTAGS\b.*",
    r"\bSOURCE_ID\b.*",
    r"\bSOURCE TYPE\b.*",
    r"\bSOURCE_TYPE\b.*",
    r"\bTHEMES\b.*",
    r"\bMODE\b.*",
    r"\bTONE\b.*",
    r"\bTITLE\b.*",
    r"\bWORK\b.*",
    r"\bSECTION\b.*",
    r"\bAUTHOR\b.*",
)

_GARBAGE_LINE_PATTERNS: tuple[str, ...] = (
    r"^\s*TITLE\s*:.*$",
    r"^\s*WORK\s*:.*$",
    r"^\s*SECTION\s*:.*$",
    r"^\s*AUTHOR\s*:.*$",
    r"^\s*THEMES\s*:.*$",
    r"^\s*MODE\s*:.*$",
    r"^\s*TONE\s*:.*$",
    r"^\s*SOURCE(?:_TYPE| TYPE)?\s*:.*$",
    r"^\s*SAFE USE NOTE\s*:.*$",
    r"^\s*MISREADING RISK\s*:.*$",
    r"^\s*USEFUL USER MESSAGES.*$",
    r"^\s*USER MESSAGE EXAMPLE\s*:.*$",
    r"^\s*USER PATTERNS\s*:.*$",
    r"^\s*PRIMARY REFERENCES\s*:.*$",
    r"^\s*TAGS\s*:.*$",
)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split()).strip()


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z\-']+", _normalize(text))
        if token not in _STOPWORDS and len(token) > 2
    ]


def _split_sentences(text: str) -> list[str]:
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]


def _trim_to_sentence_limit(text: str, max_length: int) -> str:
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return ""

    if len(normalized) <= max_length:
        if normalized[-1] not in ".!?":
            normalized += "."
        return normalized

    sentences = _split_sentences(normalized)
    if not sentences:
        fallback = normalized[:max_length].rstrip()
        last_space = fallback.rfind(" ")
        if last_space > 40:
            fallback = fallback[:last_space].rstrip()
        return fallback + "..."

    selected: list[str] = []
    total = 0

    for sentence in sentences:
        extra = len(sentence) + (1 if selected else 0)
        if total + extra > max_length:
            break
        selected.append(sentence)
        total += extra

    if selected:
        result = " ".join(selected).strip()
        if result[-1] not in ".!?":
            result += "."
        return result

    first_sentence = sentences[0]
    if len(first_sentence) <= max_length:
        return first_sentence if first_sentence[-1] in ".!?" else first_sentence + "."

    fallback = first_sentence[:max_length].rstrip()
    last_space = fallback.rfind(" ")
    if last_space > 40:
        fallback = fallback[:last_space].rstrip()
    return fallback + "..."


def _clean_chunk_text(text: str) -> str:
    cleaned = text or ""
    cleaned = cleaned.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")

    for pattern in _METADATA_CUTOFF_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)

    lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue

        if any(re.match(pattern, stripped, flags=re.IGNORECASE) for pattern in _GARBAGE_LINE_PATTERNS):
            continue

        lines.append(stripped)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    sentences = _split_sentences(cleaned)
    usable_sentences: list[str] = []

    for sentence in sentences:
        upper_ratio = sum(1 for ch in sentence if ch.isupper()) / max(1, sum(1 for ch in sentence if ch.isalpha()))
        if upper_ratio > 0.55 and len(sentence) > 30:
            continue
        if "useful user messages" in sentence.lower():
            continue
        usable_sentences.append(sentence)

    if usable_sentences:
        cleaned = " ".join(usable_sentences).strip()

    return cleaned


def _clip_text(text: str, max_length: int = 220) -> str:
    return _trim_to_sentence_limit(_clean_chunk_text(text), max_length=max_length)


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

        if haystack and any(term in haystack for term in _ALLOWED_TOPIC_TERMS):
            return True

    return False


def _build_scope_refusal() -> str:
    return (
        "That is outside this bot's scope.\n\n"
        "It only answers within the declared Nietzsche themes already defined in the corpus: "
        "comfort and complacency, excuse-making, herd mentality, conformity, ressentiment, "
        "fear of struggle, self-overcoming, and becoming who you are."
    )


def _query_overlap_score(query: str, text: str) -> float:
    query_tokens = _tokenize(query)
    text_tokens = _tokenize(text)

    if not query_tokens or not text_tokens:
        return 0.0

    query_counts = Counter(query_tokens)
    text_counts = Counter(text_tokens)

    overlap = 0
    for token, count in query_counts.items():
        overlap += min(count, text_counts.get(token, 0))

    return overlap / max(1, len(set(query_tokens)))


def _chunk_relevance_score(query: str, chunk: dict) -> float:
    raw_text = str(chunk.get("display_text") or chunk.get("text") or "").strip()
    cleaned_text = _clean_chunk_text(raw_text)

    base_score = float(chunk.get("score", 0.0) or 0.0)
    overlap_score = _query_overlap_score(query, cleaned_text)

    themes = " ".join(str(item) for item in chunk.get("themes", []))
    tags = " ".join(str(item) for item in chunk.get("tags", []))
    meta_overlap = _query_overlap_score(query, f"{themes} {tags}")

    return base_score + (overlap_score * 1.75) + (meta_overlap * 0.75)


def _rerank_chunks_for_answer(query: str, retrieved_chunks: list[dict]) -> list[dict]:
    enriched: list[tuple[float, dict]] = []

    for chunk in retrieved_chunks:
        cleaned = _clean_chunk_text(str(chunk.get("display_text") or chunk.get("text") or ""))
        if not cleaned:
            continue

        chunk_copy = dict(chunk)
        chunk_copy["cleaned_text"] = cleaned
        enriched.append((_chunk_relevance_score(query, chunk_copy), chunk_copy))

    enriched.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in enriched]


def _select_diverse_citation_chunks(
    query: str,
    retrieved_chunks: list[dict],
    max_citations: int = 3,
) -> list[dict]:
    ranked_chunks = _rerank_chunks_for_answer(query, retrieved_chunks)
    if not ranked_chunks:
        return []

    selected: list[dict] = []
    seen_sources: set[str] = set()

    for chunk in ranked_chunks:
        source_id = str(chunk.get("source_id") or "").strip()
        cleaned_text = str(chunk.get("cleaned_text") or "").strip()

        if not cleaned_text:
            continue

        if source_id and source_id in seen_sources:
            continue

        selected.append(chunk)

        if source_id:
            seen_sources.add(source_id)

        if len(selected) >= max_citations:
            break

    if len(selected) < max_citations:
        seen_chunk_ids = {str(item.get("chunk_id") or "").strip() for item in selected}
        for chunk in ranked_chunks:
            chunk_id = str(chunk.get("chunk_id") or "").strip()
            cleaned_text = str(chunk.get("cleaned_text") or "").strip()

            if not cleaned_text or chunk_id in seen_chunk_ids:
                continue

            selected.append(chunk)
            seen_chunk_ids.add(chunk_id)

            if len(selected) >= max_citations:
                break

    return selected[:max_citations]


def _format_source_label(chunk: dict) -> str:
    work = str(chunk.get("work") or "Nietzsche source").strip()
    section = str(chunk.get("section") or "").strip()
    return f"{work}, {section}" if section else work


def _build_interpretation_paragraph(
    matched_cards: list[dict],
    ranked_chunks: list[dict],
) -> str:
    top_card = matched_cards[0] if matched_cards else {}

    angle = str(top_card.get("nietzschean_angle", "")).strip()
    explanation = str(top_card.get("plain_explanation", "")).strip()

    if angle and explanation and angle != explanation:
        return f"{angle} {explanation}"

    if angle:
        return angle

    if explanation:
        return explanation

    if ranked_chunks:
        cleaned = str(ranked_chunks[0].get("cleaned_text") or "").strip()
        excerpt = _trim_to_sentence_limit(cleaned, 260)
        if excerpt:
            return f"The corpus points to a recognizable pattern here. {excerpt}"

    return "I do not have grounded Nietzsche material for that yet, so I will not fake an answer."


def _build_grounded_support_section(ranked_chunks: list[dict]) -> str:
    if not ranked_chunks:
        return ""

    parts: list[str] = []

    primary = ranked_chunks[0]
    primary_label = _format_source_label(primary)
    primary_excerpt = _trim_to_sentence_limit(str(primary.get("cleaned_text") or ""), 360)
    if primary_excerpt:
        parts.append(
            "Grounded support:\n"
            f'From "{primary_label}": "{primary_excerpt}"'
        )

    if len(ranked_chunks) > 1:
        secondary = ranked_chunks[1]
        secondary_label = _format_source_label(secondary)
        secondary_excerpt = _trim_to_sentence_limit(str(secondary.get("cleaned_text") or ""), 260)
        if secondary_excerpt:
            parts.append(
                "Second passage:\n"
                f'From "{secondary_label}": "{secondary_excerpt}"'
            )

    return "\n\n".join(parts)


def _build_conclusion_paragraph(
    matched_cards: list[dict],
    ranked_chunks: list[dict],
) -> str:
    top_card = matched_cards[0] if matched_cards else {}
    explanation = str(top_card.get("plain_explanation", "")).strip()

    if explanation:
        return explanation

    if ranked_chunks:
        return (
            "The issue is not rest by itself or strain by itself. "
            "The issue is whether comfort has been promoted from a temporary need into a ruling value."
        )

    return ""


def _build_answer(
    retrieved_chunks: list[dict],
    matched_cards: list[dict],
) -> str:
    ranked_chunks = _rerank_chunks_for_answer(
        query=" ".join(
            [
                str(matched_cards[0].get("theme", "")).strip() if matched_cards else "",
                str(retrieved_chunks[0].get("themes", [""])[0]) if retrieved_chunks and retrieved_chunks[0].get("themes") else "",
            ]
        ).strip(),
        retrieved_chunks=retrieved_chunks,
    )

    if not ranked_chunks:
        return "I do not have grounded Nietzsche material for that yet, so I will not fake an answer."

    sections: list[str] = []

    interpretation = _build_interpretation_paragraph(
        matched_cards=matched_cards,
        ranked_chunks=ranked_chunks,
    ).strip()
    if interpretation:
        sections.append(f"Reading:\n{interpretation}")

    grounded_support = _build_grounded_support_section(ranked_chunks=ranked_chunks).strip()
    if grounded_support:
        sections.append(grounded_support)

    conclusion = _build_conclusion_paragraph(
        matched_cards=matched_cards,
        ranked_chunks=ranked_chunks,
    ).strip()
    if conclusion and conclusion != interpretation:
        sections.append(f"Conclusion:\n{conclusion}")

    return "\n\n".join(section for section in sections if section.strip())


def generate_grounded_reply(message: str) -> ChatResponse:
    normalized_message = _normalize(message)

    if not _is_explicitly_in_scope(normalized_message):
        return ChatResponse(
            message=message,
            answer=_build_scope_refusal(),
            matched_card_ids=[],
            citations=[],
        )

    retrieved_chunks = search_retrieval_corpus(query=message, top_k=7)

    if not _retrieval_looks_in_scope(retrieved_chunks):
        return ChatResponse(
            message=message,
            answer=_build_scope_refusal(),
            matched_card_ids=[],
            citations=[],
        )

    ranked_chunks = _rerank_chunks_for_answer(message, retrieved_chunks)

    retrieved_source_ids = {
        str(item.get("source_id")).strip()
        for item in ranked_chunks
        if item.get("source_id")
    }

    matched_cards = find_relevant_cards(
        query=message,
        retrieved_source_ids=retrieved_source_ids,
        retrieved_chunks=ranked_chunks,
        top_k=2,
    )

    citation_chunks = _select_diverse_citation_chunks(
        query=message,
        retrieved_chunks=ranked_chunks,
        max_citations=3,
    )

    citations: list[ChatCitation] = []
    for item in citation_chunks:
        cleaned_text = str(item.get("cleaned_text") or item.get("display_text") or item.get("text") or "").strip()
        excerpt = _trim_to_sentence_limit(cleaned_text, 220)
        if not excerpt:
            continue

        citations.append(
            ChatCitation(
                source_id=item.get("source_id"),
                chunk_id=item.get("chunk_id"),
                work=item.get("work"),
                section=item.get("section"),
                score=float(item.get("score", 0.0)),
                text_excerpt=excerpt,
            )
        )

    matched_card_ids = [
        str(card.get("card_id")).strip()
        for card in matched_cards
        if str(card.get("card_id", "")).strip()
    ]

    answer = _build_answer(
        retrieved_chunks=ranked_chunks,
        matched_cards=matched_cards,
    )

    return ChatResponse(
        message=message,
        answer=answer,
        matched_card_ids=matched_card_ids,
        citations=citations,
    )