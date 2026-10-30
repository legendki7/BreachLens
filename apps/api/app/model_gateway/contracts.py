from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints


class ModelRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


NonBlankContent = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ModelMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ModelRole
    content: NonBlankContent


class ModelGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ModelMessage] = Field(min_length=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)


class ModelGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    model_id: str
    provider: str
    finish_reason: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    latency_ms: float = Field(ge=0)
    raw_metadata: dict[str, JsonValue] = Field(default_factory=dict)
