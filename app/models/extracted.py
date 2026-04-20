from pydantic import BaseModel, Field


class ExtractedDocument(BaseModel):
    source_id: str = Field(..., min_length=1)
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
    raw_text: str = Field(..., min_length=1)
    normalized_text: str = Field(..., min_length=1)