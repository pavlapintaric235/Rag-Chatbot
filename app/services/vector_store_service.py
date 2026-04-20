import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import settings
from app.models.retrieval import RetrievalResult, SearchResponse, VectorStoreStatus
from app.models.vector_document import VectorDocument
from app.services.embedding_service import get_embedding_service


def _ensure_vector_store_dirs() -> None:
    settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)


def _get_client() -> chromadb.PersistentClient:
    _ensure_vector_store_dirs()
    return chromadb.PersistentClient(path=str(settings.chroma_dir))


def _get_or_create_collection() -> Collection:
    client = _get_client()
    return client.get_or_create_collection(name=settings.chroma_collection_name)


def _reset_collection() -> Collection:
    client = _get_client()

    try:
        client.delete_collection(name=settings.chroma_collection_name)
    except Exception:
        pass

    return client.get_or_create_collection(name=settings.chroma_collection_name)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_chunk_documents() -> list[VectorDocument]:
    documents: list[VectorDocument] = []

    if not settings.chunks_dir.exists():
        return documents

    for path in sorted(settings.chunks_dir.glob("*.json")):
        source_id = path.stem
        payload = _load_json(path)

        if not isinstance(payload, list):
            continue

        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                continue

            chunk_text = _safe_str(
                item.get("chunk_text")
                or item.get("text")
                or item.get("content")
            )

            if not chunk_text:
                continue

            chunk_id = _safe_str(item.get("chunk_id")) or f"{source_id}::chunk::{index}"

            metadata: dict[str, Any] = {
                "source_type": "chunk",
                "source_id": source_id,
                "chunk_id": chunk_id,
                "file_name": path.name,
            }

            for key in (
                "title",
                "work",
                "section",
                "themes",
                "mode",
                "tone",
                "sequence",
                "start_char",
                "end_char",
            ):
                if key in item:
                    metadata[key] = item[key]

            documents.append(
                VectorDocument(
                    doc_id=chunk_id,
                    source_type="chunk",
                    source_id=source_id,
                    text=chunk_text,
                    metadata=metadata,
                )
            )

    return documents


def _build_card_documents() -> list[VectorDocument]:
    documents: list[VectorDocument] = []

    if not settings.cards_dir.exists():
        return documents

    for path in sorted(settings.cards_dir.glob("*.json")):
        payload = _load_json(path)

        if not isinstance(payload, dict):
            continue

        card_id = _safe_str(payload.get("card_id")) or path.stem
        card_text = _safe_str(payload.get("card_text"))

        if not card_text:
            continue

        metadata: dict[str, Any] = {
            "source_type": "card",
            "source_id": card_id,
            "card_id": card_id,
            "file_name": path.name,
            "theme": payload.get("theme"),
            "tags": payload.get("tags", []),
            "source_ids": payload.get("source_ids", []),
            "primary_references": payload.get("primary_references", []),
        }

        documents.append(
            VectorDocument(
                doc_id=card_id,
                source_type="card",
                source_id=card_id,
                text=card_text,
                metadata=metadata,
            )
        )

    return documents


def load_all_vector_documents() -> list[VectorDocument]:
    return _build_chunk_documents() + _build_card_documents()


def _to_chroma_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Chroma metadata values should be simple JSON-serializable primitives.
    Convert lists/dicts to JSON strings where needed.
    """
    clean: dict[str, Any] = {}

    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            clean[key] = value
        else:
            clean[key] = json.dumps(value, ensure_ascii=False)

    return clean


def build_vector_store() -> dict[str, Any]:
    """
    Rebuild the vector store from chunk and card artifacts.
    """
    documents = load_all_vector_documents()
    collection = _reset_collection()

    if not documents:
        return {
            "collection_name": settings.chroma_collection_name,
            "storage_path": str(settings.chroma_dir),
            "document_count": 0,
            "indexed_chunk_count": 0,
            "indexed_card_count": 0,
        }

    embedding_service = get_embedding_service()

    ids = [doc.doc_id for doc in documents]
    texts = [doc.text for doc in documents]
    metadatas = [_to_chroma_metadata(doc.metadata) for doc in documents]

    embeddings = embedding_service.embed_texts(texts)

    collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    chunk_count = sum(1 for doc in documents if doc.source_type == "chunk")
    card_count = sum(1 for doc in documents if doc.source_type == "card")

    return {
        "collection_name": settings.chroma_collection_name,
        "storage_path": str(settings.chroma_dir),
        "document_count": collection.count(),
        "indexed_chunk_count": chunk_count,
        "indexed_card_count": card_count,
    }


def get_vector_store_status() -> VectorStoreStatus:
    collection = _get_or_create_collection()

    return VectorStoreStatus(
        collection_name=settings.chroma_collection_name,
        storage_path=str(settings.chroma_dir),
        document_count=collection.count(),
        embedding_model_name=settings.embedding_model_name,
    )


def _parse_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}

    for key, value in raw.items():
        if not isinstance(value, str):
            parsed[key] = value
            continue

        value_strip = value.strip()

        if (
            (value_strip.startswith("[") and value_strip.endswith("]"))
            or (value_strip.startswith("{") and value_strip.endswith("}"))
        ):
            try:
                parsed[key] = json.loads(value_strip)
                continue
            except Exception:
                pass

        parsed[key] = value

    return parsed


def search_vector_store(
    query: str,
    limit: int,
    source_types: list[str] | None = None,
) -> SearchResponse:
    cleaned_query = query.strip()

    if not cleaned_query:
        return SearchResponse(query=query, total_results=0, results=[])

    collection = _get_or_create_collection()

    if collection.count() == 0:
        return SearchResponse(query=query, total_results=0, results=[])

    embedding_service = get_embedding_service()
    query_embedding = embedding_service.embed_query(cleaned_query)

    raw = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(limit * 4, 10),
        include=["documents", "metadatas", "distances"],
    )

    raw_documents = raw.get("documents", [[]])[0]
    raw_metadatas = raw.get("metadatas", [[]])[0]
    raw_distances = raw.get("distances", [[]])[0]
    raw_ids = raw.get("ids", [[]])[0]

    normalized_source_types = {item.strip().lower() for item in (source_types or []) if item.strip()}
    results: list[RetrievalResult] = []

    for doc_id, document, metadata, distance in zip(
        raw_ids,
        raw_documents,
        raw_metadatas,
        raw_distances,
    ):
        parsed_metadata = _parse_metadata(metadata or {})
        source_type = _safe_str(parsed_metadata.get("source_type")).lower()
        source_id = _safe_str(parsed_metadata.get("source_id")) or doc_id

        if normalized_source_types and source_type not in normalized_source_types:
            continue

        results.append(
            RetrievalResult(
                doc_id=doc_id,
                source_type="card" if source_type == "card" else "chunk",
                source_id=source_id,
                text=_safe_str(document),
                distance=float(distance),
                metadata=parsed_metadata,
            )
        )

        if len(results) >= limit:
            break

    return SearchResponse(
        query=cleaned_query,
        total_results=len(results),
        results=results,
    )