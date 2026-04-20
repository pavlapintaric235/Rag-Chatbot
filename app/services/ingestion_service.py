import json
from pathlib import Path

from app.core.config import settings
from app.models.extracted import ExtractedDocument
from app.models.source import SourceRecord
from app.services.source_service import load_source_manifest, resolve_source_path
from app.utils.text_utils import normalize_text


def _read_text_source(source: SourceRecord) -> str:
    """
    Read a raw text source from disk.
    """
    file_path = resolve_source_path(source.relative_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Text source file not found: {file_path}")

    return file_path.read_text(encoding="utf-8")


def _extract_source(source: SourceRecord) -> ExtractedDocument:
    """
    Extract and normalize a single source record.

    Step 3 supports only source_type='text'.
    PDF support will be added later.
    """
    if source.source_type != "text":
        raise NotImplementedError(
            f"Source type '{source.source_type}' is not supported yet in Step 3."
        )

    raw_text = _read_text_source(source)
    normalized_text = normalize_text(raw_text)

    return ExtractedDocument(
        source_id=source.source_id,
        title=source.title,
        author=source.author,
        source_type=source.source_type,
        work=source.work,
        section=source.section,
        themes=source.themes,
        mode=source.mode,
        tone=source.tone,
        safe_use_note=source.safe_use_note,
        misreading_risk=source.misreading_risk,
        raw_text=raw_text,
        normalized_text=normalized_text,
    )


def _extracted_output_path(source_id: str) -> Path:
    """
    Build the extracted JSON output path for a source.
    """
    return settings.extracted_dir / f"{source_id}.json"


def save_extracted_document(document: ExtractedDocument) -> Path:
    """
    Save an extracted document as JSON.
    """
    settings.extracted_dir.mkdir(parents=True, exist_ok=True)
    output_path = _extracted_output_path(document.source_id)

    output_path.write_text(
        json.dumps(document.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def ingest_all_sources() -> list[Path]:
    """
    Load all sources from the manifest, extract them, and save them to data/extracted.
    """
    records = load_source_manifest()
    saved_paths: list[Path] = []

    for record in records:
        extracted = _extract_source(record)
        output_path = save_extracted_document(extracted)
        saved_paths.append(output_path)

    return saved_paths