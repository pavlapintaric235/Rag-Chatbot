from pydantic import BaseModel, Field


class InterpretationCardSeed(BaseModel):
    card_id: str = Field(..., min_length=1)
    theme: str = Field(..., min_length=1)
    user_message_example: str = Field(..., min_length=1)
    user_patterns: list[str] = Field(default_factory=list)
    nietzschean_angle: str = Field(..., min_length=1)
    plain_explanation: str = Field(..., min_length=1)
    sharp_reply_style: str = Field(..., min_length=1)
    primary_references: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class InterpretationCard(BaseModel):
    card_id: str = Field(..., min_length=1)
    theme: str = Field(..., min_length=1)
    user_message_example: str = Field(..., min_length=1)
    user_patterns: list[str] = Field(default_factory=list)
    nietzschean_angle: str = Field(..., min_length=1)
    plain_explanation: str = Field(..., min_length=1)
    sharp_reply_style: str = Field(..., min_length=1)
    primary_references: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    card_text: str = Field(..., min_length=1)