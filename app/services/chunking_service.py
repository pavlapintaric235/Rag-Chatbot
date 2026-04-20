import json
from pathlib import Path

from app.core.config import settings
from app.models.chunk import DocumentChunk
from app.models.cleaned import CleanedDocument
from app.utils.text_utils import split_text_into_chunks


def _load_cleaned_document(path: Path) -> CleanedDocument:
    """
    Load a single cleaned JSON document from disk.
    """
    if not path.exists():
        raise FileNotFoundError(f"Cleaned document not found: {path}")

    raw_data = json.loads(path.read_text(encoding="utf-8"))
    return CleanedDocument.model_validate(raw_data)


def load_all_cleaned_documents() -> list[CleanedDocument]:
    """
    Load all cleaned documents from data/cleaned.
    """
    if not settings.cleaned_dir.exists():
        return []

    documents: list[CleanedDocument] = []

    for path in sorted(settings.cleaned_dir.glob("*.json")):
        documents.append(_load_cleaned_document(path))

    return documents


def build_chunks_for_document(
    document: CleanedDocument,
    target_words: int = 120,
    overlap_words: int = 25,
) -> list[DocumentChunk]:
    """
    Split one cleaned document into retrieval chunks.
    """
    split_chunks = split_text_into_chunks(
        text=document.cleaned_text,
        target_words=target_words,
        overlap_words=overlap_words,
    )

    results: list[DocumentChunk] = []

    for index, chunk_text in enumerate(split_chunks):
        chunk_id = f"{document.source_id}__chunk_{index}"

        results.append(
            DocumentChunk(
                chunk_id=chunk_id,
                source_id=document.source_id,
                chunk_index=index,
                title=document.title,
                author=document.author,
                source_type=document.source_type,
                work=document.work,
                section=document.section,
                themes=document.themes,
                mode=document.mode,
                tone=document.tone,
                safe_use_note=document.safe_use_note,
                misreading_risk=document.misreading_risk,
                chunk_text=chunk_text,
                char_count=len(chunk_text),
                word_count=len(chunk_text.split()),
            )
        )

    return results


def _chunk_output_path(source_id: str) -> Path:
    """
    Build the chunk JSON output path for a source.
    """
    return settings.chunks_dir / f"{source_id}.json"


def save_chunks_for_source(source_id: str, chunks: list[DocumentChunk]) -> Path:
    """
    Save all chunks for one source into a JSON file.
    """
    settings.chunks_dir.mkdir(parents=True, exist_ok=True)
    output_path = _chunk_output_path(source_id)

    output_path.write_text(
        json.dumps([chunk.model_dump() for chunk in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def build_all_chunks(
    target_words: int = 120,
    overlap_words: int = 25,
) -> list[Path]:
    """
    Build and save chunks for all cleaned documents.
    """
    documents = load_all_cleaned_documents()
    saved_paths: list[Path] = []

    for document in documents:
        chunks = build_chunks_for_document(
            document=document,
            target_words=target_words,
            overlap_words=overlap_words,
        )
        output_path = save_chunks_for_source(document.source_id, chunks)
        saved_paths.append(output_path)

    return saved_paths