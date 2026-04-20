from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.core.config import settings


_INLINE_HEADER_PATTERN = re.compile(
    r"^\s*"
    r"(?:TITLE:\s*.*?\s+)?"
    r"(?:WORK:\s*.*?\s+)?"
    r"(?:SECTION:\s*.*?\s+)?"
    r"(?:AUTHOR:\s*.*?\s+)?"
    r"(?:THEMES:\s*.*?\s+)?"
    r"(?:SOURCE_TYPE:\s*.*?\s+)?",
    re.IGNORECASE | re.DOTALL,
)

_METADATA_LABEL_PATTERN = re.compile(
    r"\b(TITLE|WORK|SECTION|AUTHOR|THEMES|SOURCE_TYPE):\b",
    re.IGNORECASE,
)


def _strip_inline_metadata_prefix(text: str) -> str:
    normalized = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split()).strip()

    if not normalized:
        return ""

    if not normalized.upper().startswith("TITLE:"):
        return text.strip()

    source_type_match = re.search(r"\bSOURCE_TYPE:\s*\w+\s+", normalized, re.IGNORECASE)
    if source_type_match:
        body = normalized[source_type_match.end():].strip()
        if body:
            return body

    stripped = _INLINE_HEADER_PATTERN.sub("", normalized).strip()
    if stripped and stripped != normalized:
        return stripped

    label_matches = list(_METADATA_LABEL_PATTERN.finditer(normalized))
    if len(label_matches) >= 2:
        last_match = label_matches[-1]
        trailing = normalized[last_match.end():].strip()
        parts = trailing.split(maxsplit=1)
        if len(parts) == 2:
            return parts[1].strip()
        if trailing:
            return trailing

    return text.strip()


def _normalize_chunk_record(
    source_file: Path,
    raw_chunk: dict[str, Any],
    fallback_index: int,
) -> dict[str, Any]:
    source_id = str(
        raw_chunk.get("source_id")
        or source_file.stem
    ).strip()

    chunk_id = str(
        raw_chunk.get("chunk_id")
        or f"{source_id}_chunk_{fallback_index:04d}"
    ).strip()

    text = str(
        raw_chunk.get("text")
        or raw_chunk.get("chunk_text")
        or raw_chunk.get("content")
        or ""
    ).strip()

    if not text:
        raise ValueError(
            f"Chunk '{chunk_id}' in '{source_file.name}' has no usable text field."
        )

    display_text = _strip_inline_metadata_prefix(text)

    return {
        "chunk_id": chunk_id,
        "source_id": source_id,
        "text": text,
        "display_text": display_text,
        "title": raw_chunk.get("title"),
        "work": raw_chunk.get("work"),
        "section": raw_chunk.get("section"),
        "themes": raw_chunk.get("themes", []),
        "mode": raw_chunk.get("mode"),
        "tone": raw_chunk.get("tone"),
        "tags": raw_chunk.get("tags", []),
        "metadata": raw_chunk.get("metadata", {}),
    }


def build_retrieval_corpus() -> Path:
    chunks_dir = settings.chunks_dir
    output_path = settings.retrieval_corpus_path

    if not chunks_dir.exists():
        raise FileNotFoundError(
            f"Chunks directory not found: {chunks_dir}"
        )

    chunk_files = sorted(chunks_dir.glob("*.json"))

    if not chunk_files:
        raise FileNotFoundError(
            f"No chunk files found in: {chunks_dir}"
        )

    all_chunks: list[dict[str, Any]] = []

    for chunk_file in chunk_files:
        payload = json.loads(chunk_file.read_text(encoding="utf-8"))

        if not isinstance(payload, list):
            raise ValueError(
                f"Chunk file '{chunk_file.name}' must contain a list of chunk records."
            )

        for index, raw_chunk in enumerate(payload, start=1):
            if not isinstance(raw_chunk, dict):
                raise ValueError(
                    f"Chunk file '{chunk_file.name}' contains a non-dict chunk record."
                )

            normalized = _normalize_chunk_record(
                source_file=chunk_file,
                raw_chunk=raw_chunk,
                fallback_index=index,
            )
            all_chunks.append(normalized)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    corpus = {
        "document_count": len(chunk_files),
        "chunk_count": len(all_chunks),
        "items": all_chunks,
    }

    output_path.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path