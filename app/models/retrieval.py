from pydantic import BaseModel, Field


class RetrievalQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievalResult(BaseModel):
    chunk_id: str | None = None
    source_id: str | None = None
    title: str | None = None
    work: str | None = None
    section: str | None = None
    themes: list[str] = Field(default_factory=list)
    mode: str | None = None
    tone: str | None = None
    tags: list[str] = Field(default_factory=list)
    text: str = Field(..., min_length=1)
    display_text: str | None = None
    score: float = Field(..., ge=0.0)
    vector_score: float | None = Field(default=None, ge=0.0)
    keyword_score: float | None = Field(default=None, ge=0.0)


class RetrievalQueryResponse(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(..., ge=1, le=20)
    results: list[RetrievalResult] = Field(default_factory=list)