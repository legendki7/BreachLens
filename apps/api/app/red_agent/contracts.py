from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.domain.enums import ScenarioSeverity

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
RESERVED_CREDENTIAL_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "authorization_header",
        "hf_token",
        "password",
        "secret",
        "token",
    }
)


def contains_reserved_credentials(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).strip().lower().replace("-", "_") in RESERVED_CREDENTIAL_KEYS
            or contains_reserved_credentials(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(contains_reserved_credentials(child) for child in value)
    return False


class RedAgentContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PriorTurnOutcome(StrEnum):
    SAFE_REFUSAL = "safe_refusal"
    PARTIAL_COMPLIANCE = "partial_compliance"
    COMPLIANCE = "compliance"
    UNKNOWN = "unknown"


class PriorRedAgentTurn(RedAgentContract):
    turn_number: int = Field(gt=0)
    attack_pattern_slug: NonBlankString
    attack_prompt: NonBlankString
    target_response: NonBlankString | None = None
    outcome: PriorTurnOutcome | None = None
    evaluator_feedback: NonBlankString | None = None


class RedAgentScenario(RedAgentContract):
    id: UUID | None = None
    name: NonBlankString
    slug: NonBlankString
    description: NonBlankString
    severity: ScenarioSeverity


class RedAgentAttackPattern(RedAgentContract):
    name: NonBlankString
    slug: NonBlankString
    description: NonBlankString
    category: NonBlankString | None = None


class AttackerModelConfiguration(RedAgentContract):
    canonical_model_id: NonBlankString
    provider: NonBlankString
    third_party: bool
    role: Literal["attacker"] = "attacker"
    provider_configuration: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("provider_configuration")
    @classmethod
    def reject_credentials(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if contains_reserved_credentials(value):
            raise ValueError("Attacker model configuration cannot contain credentials")
        return value


class RedAgentGenerationConfiguration(RedAgentContract):
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=512, gt=0, le=4096)


class RedAgentRequest(RedAgentContract):
    scenario: RedAgentScenario
    allowed_attack_patterns: tuple[RedAgentAttackPattern, ...]
    attack_pattern_slug: NonBlankString | None = None
    target_system_prompt: NonBlankString
    turn_number: int = Field(gt=0)
    max_turns: int = Field(gt=0)
    prior_turns: tuple[PriorRedAgentTurn, ...] = ()
    objective: NonBlankString | None = None
    contextual_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    attacker_model: AttackerModelConfiguration
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
    def validate_turn_context(self) -> RedAgentRequest:
        if self.turn_number > self.max_turns:
            raise ValueError("turn_number cannot exceed max_turns")

        prior_numbers = [turn.turn_number for turn in self.prior_turns]
        if len(prior_numbers) != len(set(prior_numbers)):
            raise ValueError("prior turn numbers must be unique")
        if any(turn_number >= self.turn_number for turn_number in prior_numbers):
            raise ValueError("prior turns must precede the requested turn")

        pattern_slugs = [pattern.slug for pattern in self.allowed_attack_patterns]
        if len(pattern_slugs) != len(set(pattern_slugs)):
            raise ValueError("allowed attack-pattern slugs must be unique")
        return self


class GeneratedAttackOutput(RedAgentContract):
    attack_prompt: NonBlankString
    strategy_summary: NonBlankString
    adaptation_reason: NonBlankString


class RedAgentResult(RedAgentContract):
    scenario_slug: NonBlankString
    attack_prompt: NonBlankString
    attack_pattern_slug: NonBlankString
    strategy_summary: NonBlankString
    adaptation_reason: NonBlankString
    turn_number: int = Field(gt=0)
    model_id: NonBlankString
    provider: NonBlankString
    latency_ms: float = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
