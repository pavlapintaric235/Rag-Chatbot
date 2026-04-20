import json

from fastapi import APIRouter

from app.core.config import settings
from app.models.chat import ChatRequest, ChatResponse
from app.models.debug import DebugInspectRequest
from app.models.retrieval import RetrievalQueryRequest, RetrievalQueryResponse
from app.services.chat_service import generate_grounded_reply
from app.services.debug_service import inspect_query
from app.services.retrieval_service import search_retrieval_corpus
from app.services.source_service import get_source_status

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sources")
def sources_endpoint() -> list[dict[str, str | bool]]:
    return get_source_status()


@router.get("/extracted")
def extracted_endpoint() -> list[dict[str, str]]:
    if not settings.extracted_dir.exists():
        return []

    items: list[dict[str, str]] = []

    for path in sorted(settings.extracted_dir.glob("*.json")):
        items.append(
            {
                "file_name": path.name,
                "path": str(path.relative_to(settings.project_root)),
            }
        )

    return items


@router.get("/extracted/{source_id}")
def extracted_document_endpoint(source_id: str) -> dict:
    file_path = settings.extracted_dir / f"{source_id}.json"

    if not file_path.exists():
        return {"error": f"Extracted file not found for source_id='{source_id}'"}

    return json.loads(file_path.read_text(encoding="utf-8"))


@router.get("/cleaned")
def cleaned_endpoint() -> list[dict[str, str]]:
    if not settings.cleaned_dir.exists():
        return []

    items: list[dict[str, str]] = []

    for path in sorted(settings.cleaned_dir.glob("*.json")):
        items.append(
            {
                "file_name": path.name,
                "path": str(path.relative_to(settings.project_root)),
            }
        )

    return items


@router.get("/cleaned/{source_id}")
def cleaned_document_endpoint(source_id: str) -> dict:
    file_path = settings.cleaned_dir / f"{source_id}.json"

    if not file_path.exists():
        return {"error": f"Cleaned file not found for source_id='{source_id}'"}

    return json.loads(file_path.read_text(encoding="utf-8"))


@router.get("/chunks")
def chunks_endpoint() -> list[dict[str, str]]:
    if not settings.chunks_dir.exists():
        return []

    items: list[dict[str, str]] = []

    for path in sorted(settings.chunks_dir.glob("*.json")):
        items.append(
            {
                "file_name": path.name,
                "path": str(path.relative_to(settings.project_root)),
            }
        )

    return items


@router.get("/chunks/{source_id}")
def chunk_document_endpoint(source_id: str) -> list[dict] | dict[str, str]:
    file_path = settings.chunks_dir / f"{source_id}.json"

    if not file_path.exists():
        return {"error": f"Chunk file not found for source_id='{source_id}'"}

    return json.loads(file_path.read_text(encoding="utf-8"))


@router.get("/cards")
def cards_endpoint() -> list[dict[str, str]]:
    if not settings.cards_dir.exists():
        return []

    items: list[dict[str, str]] = []

    for path in sorted(settings.cards_dir.glob("*.json")):
        items.append(
            {
                "file_name": path.name,
                "path": str(path.relative_to(settings.project_root)),
            }
        )

    return items


@router.get("/cards/{card_id}")
def card_document_endpoint(card_id: str) -> dict:
    file_path = settings.cards_dir / f"{card_id}.json"

    if not file_path.exists():
        return {"error": f"Card file not found for card_id='{card_id}'"}

    return json.loads(file_path.read_text(encoding="utf-8"))


@router.post("/retrieve", response_model=RetrievalQueryResponse)
def retrieve_endpoint(payload: RetrievalQueryRequest) -> RetrievalQueryResponse:
    results = search_retrieval_corpus(
        query=payload.query,
        top_k=payload.top_k,
    )
    return RetrievalQueryResponse(
        query=payload.query,
        top_k=payload.top_k,
        results=results,
    )


@router.post("/debug/inspect")
def debug_inspect_endpoint(payload: DebugInspectRequest) -> dict:
    return inspect_query(
        query=payload.query,
        top_k=payload.top_k,
    )


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    return generate_grounded_reply(payload.message)