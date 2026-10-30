from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated
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

if TYPE_CHECKING:
    from app.models.policies import PolicyProfile

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
CREDENTIAL_KEYS = frozenset(
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


def contains_credentials(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).strip().lower().replace("-", "_") in CREDENTIAL_KEYS
            or contains_credentials(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(contains_credentials(child) for child in value)
    return False


class GuardrailContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GuardrailStage(StrEnum):
    INPUT = "input"
    OUTPUT = "output"


class GuardrailDecision(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"
    MODIFY = "modify"
    FLAG = "flag"
    ERROR = "error"


class GuardrailFindingSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GuardrailScenarioContext(GuardrailContract):
    id: UUID | None = None
    name: NonBlankString
    slug: NonBlankString
    description: NonBlankString


class GuardrailPolicyContext(GuardrailContract):
    id: UUID | None = None
    name: NonBlankString
    slug: NonBlankString
    strictness_level: NonBlankString
    configuration: dict[str, JsonValue] = Field(default_factory=dict)

    @classmethod
    def from_policy_profile(
        cls,
        profile: PolicyProfile,
    ) -> GuardrailPolicyContext:
        return cls.model_validate(profile, from_attributes=True)

    @field_validator("configuration")
    @classmethod
    def reject_credentials(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if contains_credentials(value):
            raise ValueError("Policy context cannot contain credentials")
        return value


class GuardrailTargetModelContext(GuardrailContract):
    canonical_model_id: NonBlankString
    provider: NonBlankString
    third_party: bool


class GuardrailRequest(GuardrailContract):
    stage: GuardrailStage
    content: NonBlankString
    scenario: GuardrailScenarioContext
    policy_profile: GuardrailPolicyContext
    target_model: GuardrailTargetModelContext | None = None
    turn_number: int | None = Field(default=None, gt=0)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_metadata_credentials(
        cls,
        value: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        if contains_credentials(value):
            raise ValueError("Guardrail metadata cannot contain credentials")
        return value


class GuardrailFinding(GuardrailContract):
    code: NonBlankString
    name: NonBlankString
    severity: GuardrailFindingSeverity
    description: NonBlankString
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_summary: NonBlankString | None = None


class GuardrailResult(GuardrailContract):
    stage: GuardrailStage
    decision: GuardrailDecision
    original_content: str
    processed_content: str | None
    triggered_rules: tuple[str, ...] = ()
    findings: tuple[GuardrailFinding, ...] = ()
    adapter: NonBlankString
    latency_ms: float = Field(ge=0)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_decision_content(self) -> GuardrailResult:
        if self.decision in {GuardrailDecision.BLOCK, GuardrailDecision.ERROR}:
            if self.processed_content is not None:
                raise ValueError("blocked or failed content must not be processable")
        elif self.processed_content is None:
            raise ValueError("continuing decisions require processed content")
        if (
            self.decision is GuardrailDecision.MODIFY
            and self.processed_content == self.original_content
        ):
            raise ValueError("modify decisions must transform content")
        return self


class GuardrailExecutionReport(GuardrailContract):
    stage: GuardrailStage
    original_content: str
    final_content: str | None
    final_decision: GuardrailDecision
    should_continue: bool
    adapter_results: tuple[GuardrailResult, ...]
    total_latency_ms: float = Field(ge=0)
