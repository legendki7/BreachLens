from __future__ import annotations

from uuid import UUID

from app.domain.enums import DuelStatus, DuelTurnStatus
from app.duels.contracts import (
    DuelExecutionContext,
    DuelExecutionResult,
    ModelExecutionEvidence,
    StartDuelRequest,
)
from app.duels.repository import DuelRepository
from app.duels.safety import sanitize_metadata
from app.evaluation.contracts import (
    BlueEvaluationRequest,
    EvaluationAttackPattern,
    EvaluationOutcome,
    EvaluationScenario,
    PriorEvaluationTurn,
    SecurityEvaluationResult,
)
from app.evaluation.service import EvaluationService
from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailPolicyContext,
    GuardrailRequest,
    GuardrailScenarioContext,
    GuardrailStage,
    GuardrailTargetModelContext,
)
from app.guardrails.engine import GuardrailEngine
from app.model_gateway.contracts import (
    ModelGenerationRequest,
    ModelMessage,
    ModelRole,
)
from app.model_gateway.gateway import ModelGateway
from app.red_agent.contracts import (
    PriorRedAgentTurn,
    PriorTurnOutcome,
    RedAgentRequest,
    RedAgentResult,
)
from app.red_agent.service import RedAgentService


class DuelOrchestrator:
    """Coordinate existing Phase 5–7 services without duplicating their logic."""

    def __init__(
        self,
        red_agent: RedAgentService,
        guardrails: GuardrailEngine,
        model_gateway: ModelGateway,
        evaluation: EvaluationService,
        repository: DuelRepository,
    ) -> None:
        self._red_agent = red_agent
        self._guardrails = guardrails
        self._model_gateway = model_gateway
        self._evaluation = evaluation
        self._repository = repository

    async def run(
        self,
        duel_id: UUID,
        request: StartDuelRequest,
    ) -> DuelExecutionResult:
        context = await self._repository.claim_pending(duel_id)
        prior_red_turns: list[PriorRedAgentTurn] = []
        prior_evaluation_turns: list[PriorEvaluationTurn] = []

        for turn_number in range(context.completed_turns + 1, context.requested_turns + 1):
            turn_id = await self._repository.create_turn(duel_id, turn_number)
            try:
                result = await self._execute_turn(
                    context,
                    request,
                    turn_id,
                    turn_number,
                    tuple(prior_red_turns),
                    tuple(prior_evaluation_turns),
                )
            except _TurnOperationalError as exc:
                await self._repository.fail_execution(
                    duel_id,
                    turn_id,
                    exc.stage,
                    exc.category,
                    "The operational step failed; provider details were not persisted.",
                )
                return await self._repository.get_result(duel_id)
            except Exception:
                await self._repository.fail_execution(
                    duel_id,
                    turn_id,
                    "persistence",
                    "unexpected_operational_failure",
                    "The operational step failed; sensitive exception details were not persisted.",
                )
                return await self._repository.get_result(duel_id)

            red_result, evaluation_result, raw_response = result
            await self._repository.complete_turn(duel_id, turn_id)
            prior_red_turns.append(
                PriorRedAgentTurn(
                    turn_number=turn_number,
                    attack_pattern_slug=red_result.attack_pattern_slug,
                    attack_prompt=red_result.attack_prompt,
                    target_response=raw_response,
                    outcome=self._prior_red_outcome(evaluation_result),
                    evaluator_feedback=self._prior_summary(evaluation_result),
                )
            )
            prior_evaluation_turns.append(
                PriorEvaluationTurn(
                    turn_number=turn_number,
                    outcome=evaluation_result.system_outcome,
                    summary=self._prior_summary(evaluation_result),
                )
            )

            if (
                context.stop_on_first_breach
                and evaluation_result.system_outcome is EvaluationOutcome.BREACH
            ):
                await self._repository.finish_duel(duel_id, DuelStatus.STOPPED)
                return await self._repository.get_result(duel_id)

        await self._repository.finish_duel(duel_id, DuelStatus.COMPLETED)
        return await self._repository.get_result(duel_id)

    async def _execute_turn(
        self,
        context: DuelExecutionContext,
        request: StartDuelRequest,
        turn_id: UUID,
        turn_number: int,
        prior_red_turns: tuple[PriorRedAgentTurn, ...],
        prior_evaluation_turns: tuple[PriorEvaluationTurn, ...],
    ) -> tuple[RedAgentResult, SecurityEvaluationResult, str | None]:
        await self._repository.transition_turn(
            turn_id, DuelTurnStatus.GENERATING_ATTACK
        )
        try:
            red_result = await self._red_agent.generate(
                RedAgentRequest(
                    scenario=context.scenario,
                    allowed_attack_patterns=context.allowed_attack_patterns,
                    target_system_prompt=context.target_system_prompt,
                    turn_number=turn_number,
                    max_turns=context.requested_turns,
                    prior_turns=prior_red_turns,
                    attacker_model=request.attacker_model,
                    generation=request.attacker_generation,
                )
            )
            red_result = red_result.model_copy(
                update={"metadata": sanitize_metadata(red_result.metadata)}
            )
        except Exception as exc:
            raise _TurnOperationalError("red_agent", "attack_generation_failure") from exc

        pattern_id = context.attack_pattern_ids[red_result.attack_pattern_slug]
        await self._repository.save_attack(turn_id, pattern_id, red_result)

        guardrail_scenario = GuardrailScenarioContext(
            id=context.scenario.id,
            name=context.scenario.name,
            slug=context.scenario.slug,
            description=context.scenario.description,
        )
        policy = GuardrailPolicyContext(
            id=context.policy_id,
            name=context.policy_name,
            slug=context.policy_slug,
            strictness_level=context.policy_strictness,
            configuration=context.policy_configuration,
        )
        target_provider = context.target_model.provider.provider_type
        target_context = GuardrailTargetModelContext(
            canonical_model_id=context.target_model.canonical_model_id,
            provider=target_provider,
            third_party=context.target_model.third_party,
        )

        await self._repository.transition_turn(turn_id, DuelTurnStatus.SCANNING_INPUT)
        try:
            input_report = await self._guardrails.execute(
                GuardrailRequest(
                    stage=GuardrailStage.INPUT,
                    content=red_result.attack_prompt,
                    scenario=guardrail_scenario,
                    policy_profile=policy,
                    target_model=target_context,
                    turn_number=turn_number,
                )
            )
        except Exception as exc:
            raise _TurnOperationalError(
                "input_guardrails", "guardrail_execution_failure"
            ) from exc
        await self._repository.save_guardrail_report(turn_id, input_report)
        await self._repository.set_effective_prompt(turn_id, input_report.final_content)

        raw_response: str | None = None
        output_report = None
        if input_report.should_continue:
            effective_prompt = input_report.final_content
            if effective_prompt is None:
                raise _TurnOperationalError(
                    "input_guardrails", "invalid_guardrail_result"
                )
            await self._repository.transition_turn(
                turn_id, DuelTurnStatus.AWAITING_MODEL
            )
            try:
                target_result = await self._model_gateway.generate(
                    context.target_model,
                    ModelGenerationRequest(
                        messages=[
                            ModelMessage(
                                role=ModelRole.SYSTEM,
                                content=context.target_system_prompt,
                            ),
                            ModelMessage(role=ModelRole.USER, content=effective_prompt),
                        ],
                        temperature=request.target_generation.temperature,
                        max_tokens=request.target_generation.max_tokens,
                    ),
                )
            except Exception as exc:
                raise _TurnOperationalError(
                    "target_model", "target_provider_failure"
                ) from exc
            raw_response = target_result.content
            await self._repository.save_model_execution(
                turn_id,
                ModelExecutionEvidence(
                    model_id=target_result.model_id,
                    provider=target_result.provider,
                    raw_response=target_result.content,
                    system_visible_response=None,
                    finish_reason=target_result.finish_reason,
                    latency_ms=target_result.latency_ms,
                    input_tokens=target_result.input_tokens,
                    output_tokens=target_result.output_tokens,
                    total_tokens=target_result.total_tokens,
                    metadata=sanitize_metadata(target_result.raw_metadata),
                ),
            )

            await self._repository.transition_turn(
                turn_id, DuelTurnStatus.SCANNING_OUTPUT
            )
            try:
                output_report = await self._guardrails.execute(
                    GuardrailRequest(
                        stage=GuardrailStage.OUTPUT,
                        content=raw_response,
                        scenario=guardrail_scenario,
                        policy_profile=policy,
                        target_model=target_context,
                        turn_number=turn_number,
                    )
                )
            except Exception as exc:
                raise _TurnOperationalError(
                    "output_guardrails", "guardrail_execution_failure"
                ) from exc
            await self._repository.save_guardrail_report(turn_id, output_report)
            await self._repository.set_system_visible_response(
                turn_id, output_report.final_content
            )

        await self._repository.transition_turn(turn_id, DuelTurnStatus.EVALUATING)
        attack_pattern = next(
            item
            for item in context.allowed_attack_patterns
            if item.slug == red_result.attack_pattern_slug
        )
        try:
            evaluation_result = await self._evaluation.evaluate(
                BlueEvaluationRequest(
                    scenario=EvaluationScenario(
                        id=context.scenario.id,
                        name=context.scenario.name,
                        slug=context.scenario.slug,
                        description=context.scenario.description,
                    ),
                    attack_pattern=EvaluationAttackPattern(
                        id=pattern_id,
                        name=attack_pattern.name,
                        slug=attack_pattern.slug,
                        description=attack_pattern.description,
                    ),
                    attack_prompt=red_result.attack_prompt,
                    target_response=raw_response,
                    target_was_called=raw_response is not None,
                    target_system_prompt=context.target_system_prompt,
                    input_guardrail_report=input_report,
                    output_guardrail_report=output_report,
                    turn_number=turn_number,
                    prior_turns=prior_evaluation_turns,
                    trusted_context=request.trusted_evaluation_context,
                    evaluation_context={
                        **request.evaluation_context,
                        "effective_prompt": input_report.final_content,
                    },
                ),
                request.judge_model,
            )
            evaluation_result = evaluation_result.model_copy(
                update={"metadata": sanitize_metadata(evaluation_result.metadata)}
            )
        except Exception as exc:
            raise _TurnOperationalError(
                "evaluation", "evaluation_or_judge_failure"
            ) from exc
        await self._repository.save_evaluation(turn_id, evaluation_result)
        return red_result, evaluation_result, raw_response

    @staticmethod
    def _prior_red_outcome(result: SecurityEvaluationResult) -> PriorTurnOutcome:
        outcome = result.system_outcome
        if outcome is EvaluationOutcome.SAFE_REFUSAL:
            return PriorTurnOutcome.SAFE_REFUSAL
        if outcome is EvaluationOutcome.PARTIAL_COMPLIANCE:
            return PriorTurnOutcome.PARTIAL_COMPLIANCE
        if outcome is EvaluationOutcome.BREACH:
            return PriorTurnOutcome.COMPLIANCE
        return PriorTurnOutcome.UNKNOWN

    @staticmethod
    def _prior_summary(result: SecurityEvaluationResult) -> str:
        model = result.model_outcome.value if result.model_outcome else "not_evaluated"
        return (
            f"Model outcome: {model}; system outcome: {result.system_outcome.value}. "
            f"Evaluation summary: {result.judge_reason}"
        )


class _TurnOperationalError(RuntimeError):
    def __init__(self, stage: str, category: str) -> None:
        self.stage = stage
        self.category = category
        super().__init__(category)
