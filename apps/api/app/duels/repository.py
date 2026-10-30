from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.domain.enums import DuelStatus, DuelTurnStatus
from app.duels.contracts import (
    AttackEvidence,
    CreateDuelRequest,
    DuelCreated,
    DuelExecutionContext,
    DuelExecutionResult,
    DuelTurnExecutionResult,
    EvaluationEvidenceRecord,
    GuardrailEvidenceRecord,
    ModelExecutionEvidence,
    OperationalFailure,
)
from app.duels.exceptions import DuelNotFoundError, DuelReferenceNotFoundError
from app.duels.lifecycle import validate_duel_transition, validate_turn_transition
from app.duels.safety import sanitize_metadata
from app.evaluation.contracts import SecurityEvaluationResult
from app.guardrails.contracts import GuardrailExecutionReport
from app.models.duels import (
    Duel,
    DuelTurn,
    DuelTurnAttack,
    DuelTurnEvaluation,
    DuelTurnGuardrailReport,
    DuelTurnModelExecution,
)
from app.models.policies import PolicyProfile
from app.models.registry import TargetModel
from app.models.scenarios import Scenario, ScenarioAttackPattern
from app.red_agent.contracts import RedAgentAttackPattern, RedAgentResult, RedAgentScenario


class DuelRepository(Protocol):
    async def create(self, request: CreateDuelRequest) -> DuelCreated: ...
    async def claim_pending(self, duel_id: UUID) -> DuelExecutionContext: ...
    async def get_execution_context(self, duel_id: UUID) -> DuelExecutionContext: ...
    async def create_turn(self, duel_id: UUID, turn_number: int) -> UUID: ...
    async def transition_turn(self, turn_id: UUID, status: DuelTurnStatus) -> None: ...
    async def save_attack(
        self, turn_id: UUID, attack_pattern_id: UUID, result: RedAgentResult
    ) -> None: ...
    async def set_effective_prompt(self, turn_id: UUID, prompt: str | None) -> None: ...
    async def save_guardrail_report(
        self, turn_id: UUID, report: GuardrailExecutionReport
    ) -> None: ...
    async def save_model_execution(
        self, turn_id: UUID, evidence: ModelExecutionEvidence
    ) -> None: ...
    async def set_system_visible_response(
        self, turn_id: UUID, content: str | None
    ) -> None: ...
    async def save_evaluation(
        self, turn_id: UUID, result: SecurityEvaluationResult
    ) -> None: ...
    async def complete_turn(self, duel_id: UUID, turn_id: UUID) -> None: ...
    async def fail_execution(
        self,
        duel_id: UUID,
        turn_id: UUID,
        stage: str,
        category: str,
        message: str,
    ) -> None: ...
    async def finish_duel(self, duel_id: UUID, status: DuelStatus) -> None: ...
    async def get_result(self, duel_id: UUID) -> DuelExecutionResult: ...


class SqlAlchemyDuelRepository:
    """Explicit Phase 8 persistence operations, each committed as a checkpoint."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, request: CreateDuelRequest) -> DuelCreated:
        references = (
            (Scenario, request.scenario_id, "Scenario"),
            (TargetModel, request.target_model_id, "Target model"),
            (PolicyProfile, request.policy_profile_id, "Policy profile"),
        )
        for model, identifier, label in references:
            if await self._session.get(model, identifier) is None:
                raise DuelReferenceNotFoundError(f"{label} was not found")

        duel = Duel(
            scenario_id=request.scenario_id,
            target_model_id=request.target_model_id,
            policy_profile_id=request.policy_profile_id,
            requested_turns=request.requested_turns,
            stop_on_first_breach=request.stop_on_first_breach,
        )
        self._session.add(duel)
        await self._session.commit()
        await self._session.refresh(duel)
        return DuelCreated(
            duel_id=duel.id,
            status=duel.status,
            requested_turns=duel.requested_turns,
            completed_turns=duel.completed_turns,
            stop_on_first_breach=duel.stop_on_first_breach,
            created_at=duel.created_at,
        )

    async def claim_pending(self, duel_id: UUID) -> DuelExecutionContext:
        statement = self._context_statement(duel_id).with_for_update(of=Duel)
        duel = (await self._session.execute(statement)).unique().scalar_one_or_none()
        if duel is None:
            raise DuelNotFoundError(duel_id)
        validate_duel_transition(duel.status, DuelStatus.RUNNING)
        duel.status = DuelStatus.RUNNING
        duel.started_at = datetime.now(UTC)
        await self._session.commit()
        return self._to_context(duel)

    async def get_execution_context(self, duel_id: UUID) -> DuelExecutionContext:
        duel = (
            (await self._session.execute(self._context_statement(duel_id)))
            .unique()
            .scalar_one_or_none()
        )
        if duel is None:
            raise DuelNotFoundError(duel_id)
        return self._to_context(duel)

    async def create_turn(self, duel_id: UUID, turn_number: int) -> UUID:
        turn = DuelTurn(duel_id=duel_id, turn_number=turn_number)
        self._session.add(turn)
        await self._session.commit()
        await self._session.refresh(turn)
        return turn.id

    async def transition_turn(self, turn_id: UUID, status: DuelTurnStatus) -> None:
        turn = await self._require_turn(turn_id)
        validate_turn_transition(turn.status, status)
        turn.status = status
        if status is DuelTurnStatus.GENERATING_ATTACK and turn.started_at is None:
            turn.started_at = datetime.now(UTC)
        await self._session.commit()

    async def save_attack(
        self,
        turn_id: UUID,
        attack_pattern_id: UUID,
        result: RedAgentResult,
    ) -> None:
        turn = await self._require_turn(turn_id)
        turn.attack_pattern_id = attack_pattern_id
        turn.attack_prompt = result.attack_prompt
        self._session.add(
            DuelTurnAttack(
                duel_turn_id=turn_id,
                attack_pattern_id=attack_pattern_id,
                attack_prompt=result.attack_prompt,
                effective_prompt=None,
                strategy_summary=result.strategy_summary,
                adaptation_reason=result.adaptation_reason,
                attacker_model_id=result.model_id,
                attacker_provider=result.provider,
                latency_ms=result.latency_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                total_tokens=result.total_tokens,
                evidence_metadata=cast(dict[str, object], sanitize_metadata(result.metadata)),
            )
        )
        await self._session.commit()

    async def set_effective_prompt(self, turn_id: UUID, prompt: str | None) -> None:
        attack = await self._session.get(DuelTurnAttack, turn_id)
        if attack is None:
            raise DuelNotFoundError(turn_id)
        attack.effective_prompt = prompt
        await self._session.commit()

    async def save_guardrail_report(
        self,
        turn_id: UUID,
        report: GuardrailExecutionReport,
    ) -> None:
        self._session.add(
            DuelTurnGuardrailReport(
                duel_turn_id=turn_id,
                stage=report.stage.value,
                final_decision=report.final_decision.value,
                original_content=report.original_content,
                final_content=report.final_content,
                total_latency_ms=report.total_latency_ms,
                report=cast(
                    dict[str, object],
                    sanitize_metadata(report.model_dump(mode="json")),
                ),
            )
        )
        await self._session.commit()

    async def save_model_execution(
        self,
        turn_id: UUID,
        evidence: ModelExecutionEvidence,
    ) -> None:
        turn = await self._require_turn(turn_id)
        turn.target_response = evidence.raw_response
        self._session.add(
            DuelTurnModelExecution(
                duel_turn_id=turn_id,
                model_id=evidence.model_id,
                provider=evidence.provider,
                raw_response=evidence.raw_response,
                system_visible_response=evidence.system_visible_response,
                finish_reason=evidence.finish_reason,
                latency_ms=evidence.latency_ms,
                input_tokens=evidence.input_tokens,
                output_tokens=evidence.output_tokens,
                total_tokens=evidence.total_tokens,
                evidence_metadata=cast(
                    dict[str, object], sanitize_metadata(evidence.metadata)
                ),
            )
        )
        await self._session.commit()

    async def set_system_visible_response(
        self,
        turn_id: UUID,
        content: str | None,
    ) -> None:
        execution = await self._session.get(DuelTurnModelExecution, turn_id)
        if execution is None:
            raise DuelNotFoundError(turn_id)
        execution.system_visible_response = content
        await self._session.commit()

    async def save_evaluation(
        self,
        turn_id: UUID,
        result: SecurityEvaluationResult,
    ) -> None:
        self._session.add(
            DuelTurnEvaluation(
                duel_turn_id=turn_id,
                model_outcome=(result.model_outcome.value if result.model_outcome else None),
                model_attack_success_score=result.model_attack_success_score,
                system_outcome=result.system_outcome.value,
                system_attack_success_score=result.system_attack_success_score,
                confidence=result.confidence,
                rubric_id=result.rubric_id,
                rubric_version=result.rubric_version,
                judge_reason=result.judge_reason,
                judge_model_id=result.judge_model_id,
                judge_provider=result.judge_provider,
                evaluation_latency_ms=result.latency_ms,
                evidence=[item.model_dump(mode="json") for item in result.evidence],
                evaluation_metadata=cast(
                    dict[str, object], sanitize_metadata(result.metadata)
                ),
            )
        )
        await self._session.commit()

    async def complete_turn(self, duel_id: UUID, turn_id: UUID) -> None:
        turn = await self._require_turn(turn_id)
        validate_turn_transition(turn.status, DuelTurnStatus.COMPLETED)
        turn.status = DuelTurnStatus.COMPLETED
        turn.completed_at = datetime.now(UTC)
        duel = await self._require_duel(duel_id)
        duel.completed_turns += 1
        await self._session.commit()

    async def fail_execution(
        self,
        duel_id: UUID,
        turn_id: UUID,
        stage: str,
        category: str,
        message: str,
    ) -> None:
        await self._session.rollback()
        now = datetime.now(UTC)
        turn = await self._require_turn(turn_id)
        validate_turn_transition(turn.status, DuelTurnStatus.FAILED)
        turn.status = DuelTurnStatus.FAILED
        turn.failure_stage = stage
        turn.failure_category = category
        turn.failure_message = message
        turn.failed_at = now
        turn.completed_at = now
        duel = await self._require_duel(duel_id)
        validate_duel_transition(duel.status, DuelStatus.FAILED)
        duel.status = DuelStatus.FAILED
        duel.completed_at = now
        await self._session.commit()

    async def finish_duel(self, duel_id: UUID, status: DuelStatus) -> None:
        duel = await self._require_duel(duel_id)
        validate_duel_transition(duel.status, status)
        duel.status = status
        duel.completed_at = datetime.now(UTC)
        await self._session.commit()

    async def get_result(self, duel_id: UUID) -> DuelExecutionResult:
        statement = (
            select(Duel)
            .where(Duel.id == duel_id)
            .options(
                selectinload(Duel.turns).selectinload(DuelTurn.attack_evidence),
                selectinload(Duel.turns).selectinload(DuelTurn.model_execution),
                selectinload(Duel.turns).selectinload(DuelTurn.guardrail_reports),
                selectinload(Duel.turns).selectinload(DuelTurn.evaluation),
            )
        )
        duel = (await self._session.execute(statement)).unique().scalar_one_or_none()
        if duel is None:
            raise DuelNotFoundError(duel_id)
        return self._to_result(duel)

    async def _require_duel(self, duel_id: UUID) -> Duel:
        duel = await self._session.get(Duel, duel_id)
        if duel is None:
            raise DuelNotFoundError(duel_id)
        return duel

    async def _require_turn(self, turn_id: UUID) -> DuelTurn:
        turn = await self._session.get(DuelTurn, turn_id)
        if turn is None:
            raise DuelNotFoundError(turn_id)
        return turn

    @staticmethod
    def _context_statement(duel_id: UUID):
        return (
            select(Duel)
            .where(Duel.id == duel_id)
            .options(
                joinedload(Duel.scenario)
                .selectinload(Scenario.attack_pattern_links)
                .joinedload(ScenarioAttackPattern.attack_pattern),
                joinedload(Duel.target_model).joinedload(TargetModel.provider),
                joinedload(Duel.policy_profile),
            )
        )

    @staticmethod
    def _to_context(duel: Duel) -> DuelExecutionContext:
        scenario = duel.scenario
        patterns = tuple(link.attack_pattern for link in scenario.attack_pattern_links)
        return DuelExecutionContext(
            duel_id=duel.id,
            scenario=RedAgentScenario(
                id=scenario.id,
                name=scenario.name,
                slug=scenario.slug,
                description=scenario.description,
                severity=scenario.severity,
            ),
            scenario_description=scenario.description,
            target_system_prompt=scenario.target_system_prompt,
            allowed_attack_patterns=tuple(
                RedAgentAttackPattern(
                    name=item.name,
                    slug=item.slug,
                    description=item.description,
                    category=item.category,
                )
                for item in patterns
            ),
            attack_pattern_ids={item.slug: item.id for item in patterns},
            policy_id=duel.policy_profile.id,
            policy_name=duel.policy_profile.name,
            policy_slug=duel.policy_profile.slug,
            policy_strictness=duel.policy_profile.strictness_level,
            policy_configuration=duel.policy_profile.configuration,
            target_model=duel.target_model,
            requested_turns=duel.requested_turns,
            completed_turns=duel.completed_turns,
            stop_on_first_breach=duel.stop_on_first_breach,
        )

    @staticmethod
    def _to_result(duel: Duel) -> DuelExecutionResult:
        turns: list[DuelTurnExecutionResult] = []
        for turn in duel.turns:
            attack = turn.attack_evidence
            execution = turn.model_execution
            evaluation = turn.evaluation
            failure = None
            if turn.failure_stage and turn.failure_category and turn.failure_message and turn.failed_at:
                failure = OperationalFailure(
                    stage=turn.failure_stage,
                    category=turn.failure_category,
                    message=turn.failure_message,
                    occurred_at=turn.failed_at,
                )
            turns.append(
                DuelTurnExecutionResult(
                    turn_id=turn.id,
                    turn_number=turn.turn_number,
                    status=turn.status,
                    attack=(
                        AttackEvidence(
                            attack_pattern_id=attack.attack_pattern_id,
                            attack_prompt=attack.attack_prompt,
                            effective_prompt=attack.effective_prompt,
                            strategy_summary=attack.strategy_summary,
                            adaptation_reason=attack.adaptation_reason,
                            attacker_model_id=attack.attacker_model_id,
                            attacker_provider=attack.attacker_provider,
                            latency_ms=attack.latency_ms,
                            input_tokens=attack.input_tokens,
                            output_tokens=attack.output_tokens,
                            total_tokens=attack.total_tokens,
                            metadata=attack.evidence_metadata,
                        )
                        if attack
                        else None
                    ),
                    guardrail_reports=[
                        GuardrailEvidenceRecord(
                            stage=item.stage,
                            final_decision=item.final_decision,
                            original_content=item.original_content,
                            final_content=item.final_content,
                            total_latency_ms=item.total_latency_ms,
                            report=item.report,
                            created_at=item.created_at,
                        )
                        for item in sorted(turn.guardrail_reports, key=lambda item: item.stage)
                    ],
                    model_execution=(
                        ModelExecutionEvidence(
                            model_id=execution.model_id,
                            provider=execution.provider,
                            raw_response=execution.raw_response,
                            system_visible_response=execution.system_visible_response,
                            finish_reason=execution.finish_reason,
                            latency_ms=execution.latency_ms,
                            input_tokens=execution.input_tokens,
                            output_tokens=execution.output_tokens,
                            total_tokens=execution.total_tokens,
                            metadata=execution.evidence_metadata,
                        )
                        if execution
                        else None
                    ),
                    evaluation=(
                        EvaluationEvidenceRecord(
                            model_outcome=evaluation.model_outcome,
                            model_attack_success_score=evaluation.model_attack_success_score,
                            system_outcome=evaluation.system_outcome,
                            system_attack_success_score=evaluation.system_attack_success_score,
                            confidence=evaluation.confidence,
                            rubric_id=evaluation.rubric_id,
                            rubric_version=evaluation.rubric_version,
                            judge_reason=evaluation.judge_reason,
                            judge_model_id=evaluation.judge_model_id,
                            judge_provider=evaluation.judge_provider,
                            evaluation_latency_ms=evaluation.evaluation_latency_ms,
                            evidence=evaluation.evidence,
                            metadata=evaluation.evaluation_metadata,
                            created_at=evaluation.created_at,
                        )
                        if evaluation
                        else None
                    ),
                    operational_failure=failure,
                    started_at=turn.started_at,
                    completed_at=turn.completed_at,
                )
            )
        stop_reason = None
        if duel.status is DuelStatus.STOPPED:
            stop_reason = "first_system_breach"
        elif duel.status is DuelStatus.FAILED:
            stop_reason = "operational_failure"
        return DuelExecutionResult(
            duel_id=duel.id,
            status=duel.status,
            requested_turns=duel.requested_turns,
            completed_turns=duel.completed_turns,
            stop_reason=stop_reason,
            turns=turns,
            started_at=duel.started_at,
            completed_at=duel.completed_at,
        )
