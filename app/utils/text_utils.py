import re


def normalize_text(text: str) -> str:
    """
    Basic normalization used during extraction.

    Current behavior:
    - normalize line endings
    - strip leading/trailing whitespace
    - collapse excessive blank lines
    - collapse repeated spaces/tabs
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.strip()

    # Collapse repeated spaces/tabs but preserve line breaks
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse 3+ blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_text_for_rag(text: str) -> str:
    """
    Stronger cleaning pass for downstream RAG use.

    Goals:
    - keep paragraphs readable
    - remove noisy spacing artifacts
    - remove repeated blank lines
    - trim line edges
    - lightly de-hyphenate words broken across line breaks
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix basic PDF-like hyphen line breaks:
    # exam-\nple -> example
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Collapse spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Trim whitespace around line breaks
    text = re.sub(r" *\n *", "\n", text)

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip each line individually
    lines = [line.strip() for line in text.split("\n")]

    # Rebuild
    cleaned = "\n".join(lines)

    # Final cleanup of repeated blank lines again
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def split_text_into_chunks(
    text: str,
    target_words: int = 120,
    overlap_words: int = 25,
) -> list[str]:
    """
    Split text into overlapping word-based chunks.

    Why this approach:
    - simple
    - deterministic
    - easy to debug
    - good enough for MVP

    Rules:
    - split on words
    - build chunks with target_words size
    - include overlap_words between adjacent chunks
    """
    words = text.split()

    if not words:
        return []

    if target_words <= 0:
        raise ValueError("target_words must be > 0")

    if overlap_words < 0:
        raise ValueError("overlap_words must be >= 0")

    if overlap_words >= target_words:
        raise ValueError("overlap_words must be smaller than target_words")

    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = min(start + target_words, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words).strip()

        if chunk_text:
            chunks.append(chunk_text)

        if end >= len(words):
            break

        start = end - overlap_words

    return chunks