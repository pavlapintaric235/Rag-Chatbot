from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services import readiness_service

client = TestClient(app)


def test_ready_endpoint_returns_200_when_required_files_exist(tmp_path, monkeypatch) -> None:
    project_root = tmp_path
    manifests_dir = project_root / "data" / "raw" / "manifests"
    vector_store_dir = project_root / "data" / "vector_store"

    manifests_dir.mkdir(parents=True, exist_ok=True)
    vector_store_dir.mkdir(parents=True, exist_ok=True)

    sources_manifest_path = manifests_dir / "sources.json"
    cards_seed_manifest_path = manifests_dir / "cards_seed.json"
    retrieval_corpus_path = vector_store_dir / "retrieval_corpus.json"
    vectorizer_path = vector_store_dir / "tfidf_vectorizer.joblib"
    matrix_path = vector_store_dir / "tfidf_matrix.joblib"
    metadata_path = vector_store_dir / "tfidf_metadata.json"

    for path in [
        sources_manifest_path,
        cards_seed_manifest_path,
        retrieval_corpus_path,
        vectorizer_path,
        matrix_path,
        metadata_path,
    ]:
        path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(readiness_service.settings, "project_root", project_root)
    monkeypatch.setattr(readiness_service.settings, "sources_manifest_path", sources_manifest_path)
    monkeypatch.setattr(readiness_service.settings, "cards_seed_manifest_path", cards_seed_manifest_path)
    monkeypatch.setattr(readiness_service.settings, "retrieval_corpus_path", retrieval_corpus_path)
    monkeypatch.setattr(readiness_service.settings, "vectorizer_path", vectorizer_path)
    monkeypatch.setattr(readiness_service.settings, "vector_index_matrix_path", matrix_path)
    monkeypatch.setattr(readiness_service.settings, "vector_index_metadata_path", metadata_path)

    response = client.get("/ready")

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["missing_required"] == []


def test_ready_endpoint_returns_503_when_vector_index_is_missing(tmp_path, monkeypatch) -> None:
    project_root = tmp_path
    manifests_dir = project_root / "data" / "raw" / "manifests"
    vector_store_dir = project_root / "data" / "vector_store"

    manifests_dir.mkdir(parents=True, exist_ok=True)
    vector_store_dir.mkdir(parents=True, exist_ok=True)

    sources_manifest_path = manifests_dir / "sources.json"
    cards_seed_manifest_path = manifests_dir / "cards_seed.json"
    retrieval_corpus_path = vector_store_dir / "retrieval_corpus.json"
    vectorizer_path = vector_store_dir / "tfidf_vectorizer.joblib"
    matrix_path = vector_store_dir / "tfidf_matrix.joblib"
    metadata_path = vector_store_dir / "tfidf_metadata.json"

    for path in [
        sources_manifest_path,
        cards_seed_manifest_path,
        retrieval_corpus_path,
        vectorizer_path,
        metadata_path,
    ]:
        path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(readiness_service.settings, "project_root", project_root)
    monkeypatch.setattr(readiness_service.settings, "sources_manifest_path", sources_manifest_path)
    monkeypatch.setattr(readiness_service.settings, "cards_seed_manifest_path", cards_seed_manifest_path)
    monkeypatch.setattr(readiness_service.settings, "retrieval_corpus_path", retrieval_corpus_path)
    monkeypatch.setattr(readiness_service.settings, "vectorizer_path", vectorizer_path)
    monkeypatch.setattr(readiness_service.settings, "vector_index_matrix_path", matrix_path)
    monkeypatch.setattr(readiness_service.settings, "vector_index_metadata_path", metadata_path)

    response = client.get("/ready")

    assert response.status_code == 503

    payload = response.json()
    assert payload["status"] == "not_ready"
    assert "tfidf_matrix" in payload["missing_required"]