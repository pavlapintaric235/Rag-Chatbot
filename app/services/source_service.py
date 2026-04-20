import json
from pathlib import Path

from app.core.config import settings
from app.models.source import SourceRecord


def load_source_manifest() -> list[SourceRecord]:
    """
    Load and validate source records from the JSON manifest.
    """
    manifest_path = settings.sources_manifest_path

    if not manifest_path.exists():
        raise FileNotFoundError(f"Source manifest not found: {manifest_path}")

    raw_data = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, list):
        raise ValueError("Source manifest must contain a list of source objects.")

    return [SourceRecord.model_validate(item) for item in raw_data]


def resolve_source_path(relative_path: str) -> Path:
    """
    Resolve a project-relative path into an absolute path.
    """
    return settings.project_root / relative_path


def get_source_status() -> list[dict[str, str | bool]]:
    """
    Return basic file existence information for all sources.
    """
    records = load_source_manifest()
    status_rows: list[dict[str, str | bool]] = []

    for record in records:
        absolute_path = resolve_source_path(record.relative_path)
        status_rows.append(
            {
                "source_id": record.source_id,
                "title": record.title,
                "source_type": record.source_type,
                "relative_path": record.relative_path,
                "exists": absolute_path.exists(),
            }
        )

    return status_rows