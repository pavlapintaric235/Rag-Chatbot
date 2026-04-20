from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatCitation(BaseModel):
    source_id: str | None = None
    chunk_id: str | None = None
    work: str | None = None
    section: str | None = None
    score: float = Field(..., ge=0.0)
    text_excerpt: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    message: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    matched_card_ids: list[str] = Field(default_factory=list)
    citations: list[ChatCitation] = Field(default_factory=list)