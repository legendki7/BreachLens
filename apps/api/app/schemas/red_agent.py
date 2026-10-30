from __future__ import annotations

from typing import Annotated

from pydantic import Field, JsonValue, StringConstraints, field_validator, model_validator

from app.red_agent.contracts import (
    AttackerModelConfiguration,
    PriorRedAgentTurn,
    RedAgentGenerationConfiguration,
    contains_reserved_credentials,
)
from app.schemas.common import DomainSchema

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class RedAgentGenerateRequest(DomainSchema):
    """Temporary development API input for one attacker-model generation."""

    scenario_slug: NonBlankString
    attack_pattern_slug: NonBlankString | None = None
    attacker_model: AttackerModelConfiguration
    target_system_prompt: NonBlankString
    turn_number: int = Field(gt=0)
    max_turns: int = Field(gt=0)
    prior_turns: tuple[PriorRedAgentTurn, ...] = ()
    objective: NonBlankString | None = None
    contextual_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    generation: RedAgentGenerationConfiguration = Field(
        default_factory=RedAgentGenerationConfiguration
    )

    @field_validator("contextual_metadata")
    @classmethod
    def reject_metadata_credentials(
        cls,
        value: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        if contains_reserved_credentials(value):
            raise ValueError("Contextual metadata cannot contain credentials")
        return value

    @model_validator(mode="after")
    def validate_turn_context(self) -> RedAgentGenerateRequest:
        if self.turn_number > self.max_turns:
            raise ValueError("turn_number cannot exceed max_turns")
        prior_numbers = [turn.turn_number for turn in self.prior_turns]
        if len(prior_numbers) != len(set(prior_numbers)):
            raise ValueError("prior turn numbers must be unique")
        if any(turn_number >= self.turn_number for turn_number in prior_numbers):
            raise ValueError("prior turns must precede the requested turn")
        return self
