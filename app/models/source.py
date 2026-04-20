from typing import Literal

from pydantic import BaseModel, Field


SourceType = Literal["text", "pdf"]
SourceMode = Literal["warning", "diagnosis", "affirmation", "revaluation"]
SourceTone = Literal["analytic", "poetic", "sharp"]


class SourceRecord(BaseModel):
    source_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    source_type: SourceType
    file_name: str = Field(..., min_length=1)
    relative_path: str = Field(..., min_length=1)
    work: str = Field(..., min_length=1)
    section: str = Field(..., min_length=1)
    themes: list[str] = Field(default_factory=list)
    mode: SourceMode
    tone: SourceTone
    safe_use_note: str = Field(..., min_length=1)
    misreading_risk: str = Field(..., min_length=1)