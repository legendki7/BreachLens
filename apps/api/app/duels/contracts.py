from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, field_validator

from app.domain.enums import DuelStatus, DuelTurnStatus, ScenarioSeverity
from app.evaluation.contracts import (
    EvaluationOutcome,
    JudgeModelConfiguration,
    TrustedEvaluationContext,
)
from app.guardrails.contracts import GuardrailExecutionReport
from app.models.registry import TargetModel
from app.red_agent.contracts import (
    AttackerModelConfiguration,
    RedAgentAttackPattern,
    RedAgentGenerationConfiguration,
    RedAgentScenario,
    contains_reserved_credentials,
)

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DuelContract(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class CreateDuelRequest(DuelContract):
    scenario_id: UUID
    target_model_id: UUID
    policy_profile_id: UUID
    requested_turns: int = Field(gt=0)
    stop_on_first_breach: bool = True


class TargetGenerationConfiguration(DuelContract):
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0, le=4096)


class StartDuelRequest(DuelContract):
    attacker_model: AttackerModelConfiguration
    judge_model: JudgeModelConfiguration
    attacker_generation: RedAgentGenerationConfiguration = Field(
        default_factory=RedAgentGenerationConfiguration
    )
    target_generation: TargetGenerationConfiguration = Field(
        default_factory=TargetGenerationConfiguration
    )
    trusted_evaluation_context: TrustedEvaluationContext | None = None
    evaluation_context: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("evaluation_context")
    @classmethod
    def reject_credentials(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if contains_reserved_credentials(value):
            raise ValueError("Duel evaluation context cannot contain credentials")
        return value


class DuelCreated(DuelContract):
    duel_id: UUID
    status: DuelStatus
    requested_turns: int
    completed_turns: int
    stop_on_first_breach: bool
    created_at: datetime


class OperationalFailure(DuelContract):
    stage: NonBlankString
    category: NonBlankString
    message: NonBlankString
    occurred_at: datetime


class AttackEvidence(DuelContract):
    attack_pattern_id: UUID
    attack_pattern_slug: NonBlankString | None = None
    attack_prompt: NonBlankString
    effective_prompt: NonBlankString | None = None
    strategy_summary: NonBlankString
    adaptation_reason: NonBlankString
    attacker_model_id: NonBlankString
    attacker_provider: NonBlankString
    latency_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class ModelExecutionEvidence(DuelContract):
    model_id: NonBlankString
    provider: NonBlankString
    raw_response: NonBlankString
    system_visible_response: str | None = None
    finish_reason: str | None = None
    latency_ms: float = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class EvaluationEvidenceRecord(DuelContract):
    model_outcome: EvaluationOutcome | None
    model_attack_success_score: float | None = Field(default=None, ge=0, le=1)
    system_outcome: EvaluationOutcome
    system_attack_success_score: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    rubric_id: NonBlankString
    rubric_version: NonBlankString
    judge_reason: str | None = None
    judge_model_id: str | None = None
    judge_provider: str | None = None
    evaluation_latency_ms: float | None = Field(default=None, ge=0)
    evidence: list[dict[str, JsonValue]] = Field(default_factory=list)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    created_at: datetime | None = None


class GuardrailEvidenceRecord(DuelContract):
    stage: NonBlankString
    final_decision: NonBlankString
    original_content: str
    final_content: str | None
    total_latency_ms: float = Field(ge=0)
    report: dict[str, JsonValue]
    created_at: datetime | None = None


class DuelTurnExecutionResult(DuelContract):
    turn_id: UUID
    turn_number: int
    status: DuelTurnStatus
    attack: AttackEvidence | None = None
    guardrail_reports: list[GuardrailEvidenceRecord] = Field(default_factory=list)
    model_execution: ModelExecutionEvidence | None = None
    evaluation: EvaluationEvidenceRecord | None = None
    operational_failure: OperationalFailure | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class DuelExecutionResult(DuelContract):
    duel_id: UUID
    status: DuelStatus
    requested_turns: int
    completed_turns: int
    stop_reason: str | None = None
    turns: list[DuelTurnExecutionResult] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DuelExecutionContext:
    duel_id: UUID
    scenario: RedAgentScenario
    scenario_description: str
    target_system_prompt: str
    allowed_attack_patterns: tuple[RedAgentAttackPattern, ...]
    attack_pattern_ids: dict[str, UUID]
    policy_id: UUID
    policy_name: str
    policy_slug: str
    policy_strictness: str
    policy_configuration: dict[str, JsonValue]
    target_model: TargetModel
    requested_turns: int
    completed_turns: int
    stop_on_first_breach: bool

    @property
    def scenario_severity(self) -> ScenarioSeverity:
        return self.scenario.severity
