from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, JsonValue, StringConstraints, field_validator

from app.guardrails.contracts import (
    GuardrailStage,
    GuardrailTargetModelContext,
    contains_credentials,
)
from app.schemas.common import DomainSchema

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class GuardrailTestRequest(DomainSchema):
    stage: GuardrailStage
    content: NonBlankString
    scenario_slug: NonBlankString
    policy_profile_slug: NonBlankString
    target_model: GuardrailTargetModelContext | None = None
    turn_number: int | None = Field(default=None, gt=0)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    adapters: tuple[Literal["native", "nemo"], ...] | None = Field(
        default=None,
        min_length=1,
    )

    @field_validator("metadata")
    @classmethod
    def reject_metadata_credentials(
        cls,
        value: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        if contains_credentials(value):
            raise ValueError("Guardrail metadata cannot contain credentials")
        return value
