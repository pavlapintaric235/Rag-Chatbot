from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    chunk_index: int = Field(..., ge=0)

    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    source_type: str = Field(..., min_length=1)
    work: str = Field(..., min_length=1)
    section: str = Field(..., min_length=1)

    themes: list[str] = Field(default_factory=list)
    mode: str = Field(..., min_length=1)
    tone: str = Field(..., min_length=1)
    safe_use_note: str = Field(..., min_length=1)
    misreading_risk: str = Field(..., min_length=1)

    chunk_text: str = Field(..., min_length=1)
    char_count: int = Field(..., ge=1)
    word_count: int = Field(..., ge=1)