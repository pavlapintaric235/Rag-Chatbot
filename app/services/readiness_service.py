from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import settings


def _path_status(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(settings.project_root)),
        "exists": path.exists(),
        "is_file": path.is_file(),
    }


def get_readiness_report() -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {
        "sources_manifest": _path_status(settings.sources_manifest_path),
        "cards_seed_manifest": _path_status(settings.cards_seed_manifest_path),
        "retrieval_corpus": _path_status(settings.retrieval_corpus_path),
        "tfidf_vectorizer": _path_status(settings.vectorizer_path),
        "tfidf_matrix": _path_status(settings.vector_index_matrix_path),
        "tfidf_metadata": _path_status(settings.vector_index_metadata_path),
    }

    missing_required = [
        name
        for name, info in checks.items()
        if not info["exists"] or not info["is_file"]
    ]

    is_ready = len(missing_required) == 0

    return {
        "status": "ready" if is_ready else "not_ready",
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "checks": checks,
        "missing_required": missing_required,
    }