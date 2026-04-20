from typing import Any, Literal

from pydantic import BaseModel, Field


class VectorDocument(BaseModel):
    doc_id: str = Field(..., min_length=1)
    source_type: Literal["chunk", "card"]
    source_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)