"""Run a complete, explicitly mocked Phase 8 Duel with no network or database."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.enums import DuelStatus, DuelTurnStatus, ScenarioSeverity
from app.duels.contracts import (
    DuelExecutionContext,
    DuelExecutionResult,
    DuelTurnExecutionResult,
    StartDuelRequest,
)
from app.duels.lifecycle import validate_duel_transition
from app.duels.orchestrator import DuelOrchestrator
from app.evaluation.contracts import (
    EvaluationOutcome,
    JudgeModelConfiguration,
    SecurityEvaluationResult,
)
from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailExecutionReport,
    GuardrailStage,
)
from app.model_gateway.contracts import ModelGenerationResult
from app.models.registry import ModelProvider, TargetModel
from app.red_agent.contracts import (
    AttackerModelConfiguration,
    RedAgentAttackPattern,
    RedAgentResult,
    RedAgentScenario,
)


class DemoRepository:
    def __init__(self, context: DuelExecutionContext) -> None:
        self.context = context
        self.status = DuelStatus.PENDING
        self.completed_turns = 0
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.turns: dict[UUID, dict[str, object]] = {}

    async def claim_pending(self, duel_id: UUID) -> DuelExecutionContext:
        validate_duel_transition(self.status, DuelStatus.RUNNING)
        self.status = DuelStatus.RUNNING
        self.started_at = datetime.now(UTC)
        return self.context

    async def create_turn(self, duel_id: UUID, turn_number: int) -> UUID:
        turn_id = uuid4()
        self.turns[turn_id] = {
            "number": turn_number,
            "status": DuelTurnStatus.PENDING,
            "started_at": None,
            "completed_at": None,
        }
        print(f"\nTurn {turn_number}")
        return turn_id

    async def transition_turn(self, turn_id: UUID, status: DuelTurnStatus) -> None:
        self.turns[turn_id]["status"] = status
        if status is DuelTurnStatus.GENERATING_ATTACK:
            self.turns[turn_id]["started_at"] = datetime.now(UTC)

    async def save_attack(self, turn_id: UUID, pattern_id: UUID, result: RedAgentResult) -> None:
        print(f"  Attack generated ({result.attack_pattern_slug}): {result.attack_prompt}")

    async def set_effective_prompt(self, turn_id: UUID, prompt: str | None) -> None:
        self.turns[turn_id]["effective_prompt"] = prompt

    async def save_guardrail_report(self, turn_id: UUID, report: GuardrailExecutionReport) -> None:
        print(f"  {report.stage.value.title()} guardrail: {report.final_decision.value}")

    async def save_model_execution(self, turn_id: UUID, evidence) -> None:
        self.turns[turn_id]["raw_response"] = evidence.raw_response
        print(f"  Target response (mock): {evidence.raw_response}")

    async def set_system_visible_response(self, turn_id: UUID, content: str | None) -> None:
        self.turns[turn_id]["system_visible_response"] = content

    async def save_evaluation(self, turn_id: UUID, result: SecurityEvaluationResult) -> None:
        self.turns[turn_id]["evaluation"] = result
        model = result.model_outcome.value if result.model_outcome else "not_evaluated"
        print(f"  Evaluation: model={model}, system={result.system_outcome.value}")

    async def complete_turn(self, duel_id: UUID, turn_id: UUID) -> None:
        self.turns[turn_id]["status"] = DuelTurnStatus.COMPLETED
        self.turns[turn_id]["completed_at"] = datetime.now(UTC)
        self.completed_turns += 1

    async def fail_execution(self, duel_id, turn_id, stage, category, message) -> None:
        self.status = DuelStatus.FAILED
        self.turns[turn_id]["status"] = DuelTurnStatus.FAILED
        self.completed_at = datetime.now(UTC)

    async def finish_duel(self, duel_id: UUID, status: DuelStatus) -> None:
        validate_duel_transition(self.status, status)
        self.status = status
        self.completed_at = datetime.now(UTC)

    async def get_result(self, duel_id: UUID) -> DuelExecutionResult:
        return DuelExecutionResult(
            duel_id=duel_id,
            status=self.status,
            requested_turns=self.context.requested_turns,
            completed_turns=self.completed_turns,
            stop_reason=(
                "first_system_breach" if self.status is DuelStatus.STOPPED else None
            ),
            turns=[
                DuelTurnExecutionResult(
                    turn_id=turn_id,
                    turn_number=data["number"],
                    status=data["status"],
                    started_at=data["started_at"],
                    completed_at=data["completed_at"],
                )
                for turn_id, data in self.turns.items()
            ],
            started_at=self.started_at,
            completed_at=self.completed_at,
        )


class DemoRedAgent:
    async def generate(self, request):
        pattern = request.allowed_attack_patterns[request.turn_number - 1]
        adaptation = (
            "Initial mock strategy"
            if not request.prior_turns
            else "Mock adaptation based on the prior safe refusal"
        )
        return RedAgentResult(
            scenario_slug=request.scenario.slug,
            attack_prompt=f"mock attack prompt {request.turn_number}",
            attack_pattern_slug=pattern.slug,
            strategy_summary=f"Mock {pattern.name}",
            adaptation_reason=adaptation,
            turn_number=request.turn_number,
            model_id="mock/attacker",
            provider="mock",
            latency_ms=0,
            metadata={"mock": True},
        )


class DemoGuardrails:
    async def execute(self, request):
        return GuardrailExecutionReport(
            stage=request.stage,
            original_content=request.content,
            final_content=request.content,
            final_decision=GuardrailDecision.ALLOW,
            should_continue=True,
            adapter_results=(),
            total_latency_ms=0,
        )


class DemoGateway:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, model, request):
        self.calls += 1
        response = (
            "I cannot comply with that request."
            if self.calls == 1
            else "Mock vulnerable response for orchestration testing only."
        )
        return ModelGenerationResult(
            content=response,
            model_id=model.canonical_model_id,
            provider="mock",
            finish_reason="stop",
            latency_ms=0,
            raw_metadata={"mock": True},
        )


class DemoEvaluation:
    def __init__(self) -> None:
        self.calls = 0

    async def evaluate(self, request, judge_model):
        self.calls += 1
        outcome = (
            EvaluationOutcome.SAFE_REFUSAL
            if self.calls == 1
            else EvaluationOutcome.BREACH
        )
        score = 0.0 if outcome is EvaluationOutcome.SAFE_REFUSAL else 1.0
        return SecurityEvaluationResult(
            model_outcome=outcome,
            model_attack_success_score=score,
            model_resilience_evaluated=True,
            system_outcome=outcome,
            system_attack_success_score=score,
            confidence=1,
            judge_reason="Deterministic mock evaluation result.",
            evidence=(),
            rubric_id="rta:mock-demo",
            rubric_version="1.0.0",
            judge_model_id=judge_model.canonical_model_id,
            judge_provider=judge_model.provider,
            latency_ms=0,
            metadata={"mock": True},
        )


def demo_context() -> DuelExecutionContext:
    provider = ModelProvider(
        name="Mock",
        slug="mock",
        provider_type="mock",
        is_active=True,
    )
    target = TargetModel(
        provider=provider,
        display_name="Mock Target",
        canonical_model_id="mock/target",
        third_party=False,
        is_active=True,
        configuration={},
    )
    patterns = (
        RedAgentAttackPattern(name="Role Play", slug="role-play", description="Mock role play"),
        RedAgentAttackPattern(name="Escalation", slug="escalation", description="Mock escalation"),
    )
    return DuelExecutionContext(
        duel_id=uuid4(),
        scenario=RedAgentScenario(
            id=uuid4(),
            name="Mock Jailbreak",
            slug="jailbreak",
            description="Offline orchestration demonstration",
            severity=ScenarioSeverity.CRITICAL,
        ),
        scenario_description="Offline orchestration demonstration",
        target_system_prompt="Mock target safety prompt.",
        allowed_attack_patterns=patterns,
        attack_pattern_ids={pattern.slug: uuid4() for pattern in patterns},
        policy_id=uuid4(),
        policy_name="Mock Strict",
        policy_slug="mock-strict",
        policy_strictness="strict",
        policy_configuration={},
        target_model=target,
        requested_turns=2,
        completed_turns=0,
        stop_on_first_breach=True,
    )


async def main() -> None:
    print("MOCK ORCHESTRATION DEMO")
    print("No result below is real assessment evidence.")
    context = demo_context()
    repository = DemoRepository(context)
    orchestrator = DuelOrchestrator(
        DemoRedAgent(),
        DemoGuardrails(),
        DemoGateway(),
        DemoEvaluation(),
        repository,
    )
    result = await orchestrator.run(
        context.duel_id,
        StartDuelRequest(
            attacker_model=AttackerModelConfiguration(
                canonical_model_id="mock/attacker",
                provider="mock",
                third_party=False,
            ),
            judge_model=JudgeModelConfiguration(
                canonical_model_id="mock/judge",
                provider="mock",
                third_party=False,
            ),
        ),
    )
    print(
        f"\nMock Duel result: status={result.status.value}, "
        f"completed_turns={result.completed_turns}, stop_reason={result.stop_reason}"
    )


if __name__ == "__main__":
    asyncio.run(main())
