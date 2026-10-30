from __future__ import annotations

import re
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

from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailExecutionReport,
    contains_credentials,
)

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TOKEN_LIKE_VALUE = re.compile(
    r"(?:\b(?:sk-|hf_)[A-Za-z0-9_-]{16,}\b|"
    r"\bBearer\s+[A-Za-z0-9._-]{16,})",
    re.IGNORECASE,
)


def contains_token_like_value(value: object) -> bool:
    if isinstance(value, str):
        return TOKEN_LIKE_VALUE.search(value) is not None
    if isinstance(value, dict):
        return any(contains_token_like_value(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_token_like_value(child) for child in value)
    return False


class EvaluationContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvaluationOutcome(StrEnum):
    BLOCKED_BY_GUARDRAIL = "blocked_by_guardrail"
    SAFE_REFUSAL = "safe_refusal"
    SAFE_RESPONSE = "safe_response"
    PARTIAL_COMPLIANCE = "partial_compliance"
    BREACH = "breach"
    INCONCLUSIVE = "inconclusive"
    ERROR = "error"


class EvaluationEvidenceSource(StrEnum):
    TARGET_RESPONSE = "target_response"
    INPUT_GUARDRAIL = "input_guardrail"
    OUTPUT_GUARDRAIL = "output_guardrail"
    DETERMINISTIC_CHECK = "deterministic_check"
    EVALUATOR = "evaluator"


class EvaluationEvidenceSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvaluationScenario(EvaluationContract):
    id: UUID | None = None
    name: NonBlankString
    slug: NonBlankString
    description: NonBlankString


class EvaluationAttackPattern(EvaluationContract):
    id: UUID | None = None
    name: NonBlankString
    slug: NonBlankString
    description: NonBlankString


class PriorEvaluationTurn(EvaluationContract):
    turn_number: int = Field(gt=0)
    outcome: EvaluationOutcome | None = None
    summary: NonBlankString


class TrustedEvaluationContext(EvaluationContract):
    protected_values: tuple[NonBlankString, ...] = ()
    expected_behavior_specification: NonBlankString | None = None
    trusted_facts: dict[str, NonBlankString] = Field(default_factory=dict)
    compliance_indicators: tuple[NonBlankString, ...] = ()
    indirect_content_source: NonBlankString | None = None
    additional_context: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_infrastructure_credentials(self) -> TrustedEvaluationContext:
        structured_values: object = {
            "trusted_facts": self.trusted_facts,
            "additional_context": self.additional_context,
        }
        if contains_credentials(structured_values):
            raise ValueError("Trusted evaluation context cannot contain credentials")
        all_values = {
            "protected_values": self.protected_values,
            "expected_behavior_specification": self.expected_behavior_specification,
            "trusted_facts": self.trusted_facts,
            "compliance_indicators": self.compliance_indicators,
            "indirect_content_source": self.indirect_content_source,
            "additional_context": self.additional_context,
        }
        if contains_token_like_value(all_values):
            raise ValueError(
                "Trusted evaluation context cannot contain infrastructure credentials"
            )
        return self


class BlueEvaluationRequest(EvaluationContract):
    scenario: EvaluationScenario
    attack_pattern: EvaluationAttackPattern
    attack_prompt: NonBlankString
    target_response: NonBlankString | None = None
    target_was_called: bool
    target_system_prompt: NonBlankString | None = None
    input_guardrail_report: GuardrailExecutionReport | None = None
    output_guardrail_report: GuardrailExecutionReport | None = None
    turn_number: int = Field(gt=0)
    prior_turns: tuple[PriorEvaluationTurn, ...] = ()
    trusted_context: TrustedEvaluationContext | None = None
    evaluation_context: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("evaluation_context")
    @classmethod
    def reject_context_credentials(
        cls,
        value: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        if contains_credentials(value):
            raise ValueError("Evaluation context cannot contain credentials")
        return value

    @model_validator(mode="after")
    def validate_interaction_state(self) -> BlueEvaluationRequest:
        if not self.target_was_called and self.target_response is not None:
            raise ValueError("A target response requires target execution")
        if not self.target_was_called and self.output_guardrail_report is not None:
            raise ValueError("Output guardrails require target execution")
        if (
            self.input_guardrail_report is not None
            and self.input_guardrail_report.stage.value != "input"
        ):
            raise ValueError("Input guardrail report has the wrong stage")
        if (
            self.output_guardrail_report is not None
            and self.output_guardrail_report.stage.value != "output"
        ):
            raise ValueError("Output guardrail report has the wrong stage")
        if (
            self.input_guardrail_report is not None
            and self.input_guardrail_report.final_decision
            is GuardrailDecision.BLOCK
            and self.target_was_called
        ):
            raise ValueError("Target cannot be called after an input guardrail block")
        prior_numbers = [turn.turn_number for turn in self.prior_turns]
        if len(prior_numbers) != len(set(prior_numbers)):
            raise ValueError("Prior evaluation turn numbers must be unique")
        if any(number >= self.turn_number for number in prior_numbers):
            raise ValueError("Prior evaluation turns must precede the current turn")
        return self


class EvaluationEvidence(EvaluationContract):
    code: NonBlankString
    category: NonBlankString
    severity: EvaluationEvidenceSeverity
    description: NonBlankString
    source: EvaluationEvidenceSource
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_summary: NonBlankString | None = None


class BlueEvaluationResult(EvaluationContract):
    signals: tuple[NonBlankString, ...]
    evidence: tuple[EvaluationEvidence, ...]
    target_was_called: bool
    target_response_available: bool
    refusal_detected: bool
    possible_compliance: bool
    possible_sensitive_disclosure: bool
    possible_hidden_context_exposure: bool
    guardrail_intervention: bool
    concise_summary: NonBlankString
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class JudgeGenerationConfiguration(EvaluationContract):
    temperature: float = Field(default=0.0, ge=0, le=2)
    max_tokens: int = Field(default=800, gt=0, le=4096)


class JudgeModelConfiguration(EvaluationContract):
    canonical_model_id: NonBlankString
    provider: NonBlankString
    third_party: bool
    role: Literal["judge"] = "judge"
    generation: JudgeGenerationConfiguration = Field(
        default_factory=JudgeGenerationConfiguration
    )
    provider_configuration: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("provider_configuration")
    @classmethod
    def reject_credentials(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if contains_credentials(value):
            raise ValueError("Judge model configuration cannot contain credentials")
        return value


class JudgeStructuredOutput(EvaluationContract):
    model_outcome: EvaluationOutcome
    model_attack_success_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    reason: NonBlankString
    evidence_codes: tuple[NonBlankString, ...]


class ModelJudgmentResult(EvaluationContract):
    model_outcome: EvaluationOutcome
    model_attack_success_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    judge_reason: NonBlankString
    evidence: tuple[EvaluationEvidence, ...]
    rubric_id: NonBlankString
    rubric_version: NonBlankString
    judge_model_id: NonBlankString
    judge_provider: NonBlankString
    latency_ms: float = Field(ge=0)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class SecurityEvaluationResult(EvaluationContract):
    model_outcome: EvaluationOutcome | None
    model_attack_success_score: float | None = Field(default=None, ge=0, le=1)
    model_resilience_evaluated: bool
    system_outcome: EvaluationOutcome
    system_attack_success_score: float | None = Field(default=None, ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    judge_reason: NonBlankString
    evidence: tuple[EvaluationEvidence, ...]
    rubric_id: NonBlankString
    rubric_version: NonBlankString
    judge_model_id: NonBlankString | None = None
    judge_provider: NonBlankString | None = None
    latency_ms: float = Field(ge=0)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dual_outcome(self) -> SecurityEvaluationResult:
        if self.model_resilience_evaluated:
            if self.model_outcome is None:
                raise ValueError("Evaluated model resilience requires an outcome")
            if self.model_outcome is EvaluationOutcome.BLOCKED_BY_GUARDRAIL:
                raise ValueError("A model outcome cannot be blocked_by_guardrail")
            if (
                self.model_attack_success_score is None
                and self.model_outcome
                not in {EvaluationOutcome.INCONCLUSIVE, EvaluationOutcome.ERROR}
            ):
                raise ValueError("Conclusive model outcomes require an attack-success score")
        elif self.model_outcome is not None or self.model_attack_success_score is not None:
            raise ValueError("Unevaluated model resilience cannot have an outcome or score")
        if (
            self.system_attack_success_score is None
            and self.system_outcome
            not in {EvaluationOutcome.INCONCLUSIVE, EvaluationOutcome.ERROR}
        ):
            raise ValueError("Conclusive system outcomes require an attack-success score")
        if (self.judge_model_id is None) != (self.judge_provider is None):
            raise ValueError("Judge model ID and provider must be recorded together")
        return self
