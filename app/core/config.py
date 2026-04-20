from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _load_dotenv() -> None:
    """
    Load environment variables from the project root .env file if present.
    Falls back to default dotenv loading otherwise.
    """
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[2]
    env_path = project_root / ".env"

    if env_path.exists() and env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=False)
    else:
        load_dotenv(override=False)


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default

    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


_load_dotenv()


class Settings:
    """
    Application settings loaded from environment variables.

    Rules:
    - PORT takes precedence for deployment platforms like Render.
    - APP_PORT is used for local development when PORT is not set.
    """

    def __init__(self) -> None:
        self.project_root: Path = Path(__file__).resolve().parents[2]

        self.app_name: str = os.getenv("APP_NAME", "Nietzsche RAG Bot")
        self.app_env: str = os.getenv("APP_ENV", "development").strip().lower()
        self.debug: bool = _parse_bool(os.getenv("DEBUG"), default=False)

        default_host = "127.0.0.1" if self.app_env == "development" else "0.0.0.0"
        self.app_host: str = (os.getenv("APP_HOST") or default_host).strip() or default_host

        port_from_env = os.getenv("PORT")
        app_port_from_env = os.getenv("APP_PORT")
        self.app_port: int = _parse_int(
            port_from_env,
            default=_parse_int(app_port_from_env, 8000),
        )

        self.data_dir: Path = self.project_root / "data"
        self.raw_dir: Path = self.data_dir / "raw"
        self.raw_pdfs_dir: Path = self.raw_dir / "pdfs"
        self.raw_text_dir: Path = self.raw_dir / "text"
        self.raw_manifests_dir: Path = self.raw_dir / "manifests"

        self.extracted_dir: Path = self.data_dir / "extracted"
        self.cleaned_dir: Path = self.data_dir / "cleaned"
        self.chunks_dir: Path = self.data_dir / "chunks"
        self.cards_dir: Path = self.data_dir / "cards"
        self.vector_store_dir: Path = self.data_dir / "vector_store"

        self.sources_manifest_path: Path = self.raw_manifests_dir / "sources.json"
        self.cards_seed_manifest_path: Path = self.raw_manifests_dir / "cards_seed.json"

        self.retrieval_corpus_path: Path = self.vector_store_dir / "retrieval_corpus.json"
        self.vectorizer_path: Path = self.vector_store_dir / "tfidf_vectorizer.joblib"
        self.tfidf_matrix_path: Path = self.vector_store_dir / "tfidf_matrix.joblib"
        self.tfidf_metadata_path: Path = self.vector_store_dir / "tfidf_metadata.json"

        # Backward-compatible aliases for existing service code.
        self.vector_index_matrix_path: Path = self.tfidf_matrix_path
        self.vector_index_metadata_path: Path = self.tfidf_metadata_path


settings = Settings()