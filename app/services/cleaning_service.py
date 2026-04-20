from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.core.config import settings


_POWERSHELL_PROMPT_PATTERN = re.compile(
    r"^\([^)]*\)\s+PS\s+[A-Za-z]:\\.*?>\s*$|^PS\s+[A-Za-z]:\\.*?>\s*$",
    re.IGNORECASE,
)

_SHELL_NOISE_PREFIXES = (
    "invoke-restmethod",
    "get-content",
    "get-childitem",
    "measure-object",
    "select-object",
    "convertto-json",
    "python -m",
    "uvicorn ",
    "curl ",
)

_COMMON_REPLACEMENTS: dict[str, str] = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2026": "...",
    "\xa0": " ",
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€": '"',
    "â€“": "-",
    "â€”": "-",
    "â€¦": "...",
    "Ã©": "é",
    "Ã¨": "è",
    "Ãª": "ê",
    "Ã«": "ë",
    "Ã¡": "á",
    "Ã ": "à",
    "Ã¢": "â",
    "Ã¤": "ä",
    "Ã¶": "ö",
    "Ã¼": "ü",
    "Ã±": "ñ",
    "donât": "don't",
    "canât": "can't",
    "wonât": "won't",
    "isnât": "isn't",
    "arenât": "aren't",
    "doesnât": "doesn't",
    "didnât": "didn't",
    "Iâm": "I'm",
    "Iâd": "I'd",
    "Iâll": "I'll",
    "Iâve": "I've",
    "youâre": "you're",
    "youâve": "you've",
    "thatâs": "that's",
    "thereâs": "there's",
    "whatâs": "what's",
    "itâs": "it's",
}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected dict JSON in extracted file: {path.name}")
    return payload


def _extract_raw_text(payload: dict[str, Any]) -> str:
    candidate_fields = [
        "extracted_text",
        "raw_text",
        "cleaned_text",
        "text",
        "content",
        "body",
    ]

    for field_name in candidate_fields:
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            return value

    return ""


def _looks_like_mojibake(text: str) -> bool:
    suspicious_markers = [
        "â",
        "Ã",
        "�",
    ]
    return any(marker in text for marker in suspicious_markers)


def _try_fix_utf8_latin1_roundtrip(text: str) -> str:
    try:
        repaired = text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
        return repaired if repaired.strip() else text
    except Exception:
        return text


def _repair_mojibake(text: str) -> str:
    repaired = text

    if _looks_like_mojibake(repaired):
        roundtrip = _try_fix_utf8_latin1_roundtrip(repaired)
        if roundtrip:
            repaired = roundtrip

    for bad, good in _COMMON_REPLACEMENTS.items():
        repaired = repaired.replace(bad, good)

    return repaired


def _is_shell_noise_line(line: str) -> bool:
    stripped = line.strip()

    if not stripped:
        return False

    if _POWERSHELL_PROMPT_PATTERN.match(stripped):
        return True

    lowered = stripped.lower()

    if any(lowered.startswith(prefix) for prefix in _SHELL_NOISE_PREFIXES):
        return True

    if "PS C:\\" in stripped or "PS C:/" in stripped:
        return True

    return False


def _remove_shell_noise(text: str) -> str:
    kept_lines: list[str] = []

    for line in text.splitlines():
        if _is_shell_noise_line(line):
            continue
        kept_lines.append(line)

    return "\n".join(kept_lines)


def _normalize_line_spacing(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]

    collapsed_lines: list[str] = []
    previous_blank = False

    for line in lines:
        is_blank = not line.strip()

        if is_blank and previous_blank:
            continue

        collapsed_lines.append(line)
        previous_blank = is_blank

    return "\n".join(collapsed_lines).strip()


def _normalize_inline_spacing(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return text.strip()


def _clean_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _repair_mojibake(cleaned)
    cleaned = _remove_shell_noise(cleaned)
    cleaned = _repair_mojibake(cleaned)
    cleaned = _normalize_inline_spacing(cleaned)
    cleaned = _normalize_line_spacing(cleaned)
    return cleaned


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []

    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)

    return normalized


def _clean_optional_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback

    text = str(value)
    if not text.strip():
        return fallback

    cleaned = _clean_text(text)
    return cleaned if cleaned else fallback


def _build_cleaned_payload(source_file: Path, payload: dict[str, Any]) -> dict[str, Any]:
    extracted_text = _extract_raw_text(payload)
    cleaned_text = _clean_text(extracted_text)

    source_id = str(payload.get("source_id") or source_file.stem).strip()

    return {
        "source_id": source_id,
        "title": payload.get("title"),
        "author": payload.get("author"),
        "work": payload.get("work"),
        "section": payload.get("section"),
        "themes": _normalize_string_list(payload.get("themes", [])),
        "tags": _normalize_string_list(payload.get("tags", [])),
        "mode": payload.get("mode"),
        "tone": payload.get("tone"),
        "source_type": payload.get("source_type"),
        "file_name": payload.get("file_name"),
        "relative_path": payload.get("relative_path"),
        "safe_use_note": _clean_optional_text(
            payload.get("safe_use_note"),
            fallback="Use Nietzsche as diagnosis and provocation, not as permission for cruelty, domination, or simplification.",
        ),
        "misreading_risk": _clean_optional_text(
            payload.get("misreading_risk"),
            fallback="Do not flatten Nietzsche into self-help slogans, nihilism, or brute-force toughness.",
        ),
        "extracted_text": cleaned_text,
        "cleaned_text": cleaned_text,
        "text": cleaned_text,
        "raw_text_length": len(extracted_text),
        "cleaned_text_length": len(cleaned_text),
    }


def clean_all_extracted_documents() -> list[Path]:
    extracted_dir = settings.extracted_dir
    cleaned_dir = settings.cleaned_dir

    if not extracted_dir.exists():
        raise FileNotFoundError(f"Extracted directory not found: {extracted_dir}")

    extracted_files = sorted(extracted_dir.glob("*.json"))

    if not extracted_files:
        raise FileNotFoundError(f"No extracted JSON files found in: {extracted_dir}")

    cleaned_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []

    for extracted_file in extracted_files:
        payload = _read_json(extracted_file)
        cleaned_payload = _build_cleaned_payload(extracted_file, payload)

        output_path = cleaned_dir / extracted_file.name
        output_path.write_text(
            json.dumps(cleaned_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        saved_paths.append(output_path)

    return saved_paths