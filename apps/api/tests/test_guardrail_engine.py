import asyncio
from collections.abc import Callable

from app.guardrails.adapter import GuardrailAdapter
from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailFinding,
    GuardrailFindingSeverity,
    GuardrailPolicyContext,
    GuardrailRequest,
    GuardrailResult,
    GuardrailScenarioContext,
    GuardrailStage,
)
from app.guardrails.engine import GuardrailEngine


class FakeAdapter(GuardrailAdapter):
    def __init__(
        self,
        name: str,
        decision: GuardrailDecision,
        calls: list[tuple[str, str]],
        transform: Callable[[str], str] | None = None,
        *,
        fail: bool = False,
    ) -> None:
        self.name = name
        self.decision = decision
        self.calls = calls
        self.transform = transform
        self.fail = fail

    async def apply(self, request: GuardrailRequest) -> GuardrailResult:
        self.calls.append((self.name, request.content))
        if self.fail:
            raise RuntimeError("private adapter failure")
        processed = request.content
        if self.decision is GuardrailDecision.MODIFY and self.transform is not None:
            processed = self.transform(processed)
        if self.decision in {GuardrailDecision.BLOCK, GuardrailDecision.ERROR}:
            processed = None
        findings = ()
        if self.decision is not GuardrailDecision.ALLOW:
            findings = (
                GuardrailFinding(
                    code=f"{self.name.upper()}_FINDING",
                    name="Test finding",
                    severity=GuardrailFindingSeverity.HIGH,
                    description="Test adapter evidence.",
                    confidence=0.9,
                ),
            )
        return GuardrailResult(
            stage=request.stage,
            decision=self.decision,
            original_content=request.content,
            processed_content=processed,
            triggered_rules=tuple(finding.code for finding in findings),
            findings=findings,
            adapter=self.name,
            latency_ms=1,
        )


def request(*, nemo_enabled: bool = False) -> GuardrailRequest:
    return GuardrailRequest(
        stage=GuardrailStage.INPUT,
        content="original content",
        scenario=GuardrailScenarioContext(
            name="Jailbreak",
            slug="jailbreak",
            description="Test instruction bypass.",
        ),
        policy_profile=GuardrailPolicyContext(
            name="Strict",
            slug="strict",
            strictness_level="strict",
            configuration={"nemo_enabled": nemo_enabled},
        ),
    )


def test_engine_executes_adapters_in_order_and_aggregates_allow_evidence() -> None:
    calls: list[tuple[str, str]] = []
    engine = GuardrailEngine(
        (
            FakeAdapter("native", GuardrailDecision.ALLOW, calls),
            FakeAdapter("nemo", GuardrailDecision.ALLOW, calls),
        )
    )

    report = asyncio.run(engine.execute(request(nemo_enabled=True)))

    assert calls == [("native", "original content"), ("nemo", "original content")]
    assert [result.adapter for result in report.adapter_results] == ["native", "nemo"]
    assert report.final_decision is GuardrailDecision.ALLOW
    assert report.final_content == "original content"
    assert report.should_continue is True


def test_engine_stops_after_enforced_block() -> None:
    calls: list[tuple[str, str]] = []
    engine = GuardrailEngine(
        (
            FakeAdapter("native", GuardrailDecision.BLOCK, calls),
            FakeAdapter("nemo", GuardrailDecision.ALLOW, calls),
        )
    )

    report = asyncio.run(engine.execute(request(nemo_enabled=True)))

    assert calls == [("native", "original content")]
    assert report.final_decision is GuardrailDecision.BLOCK
    assert report.final_content is None
    assert report.should_continue is False


def test_engine_passes_modified_content_to_the_next_adapter() -> None:
    calls: list[tuple[str, str]] = []
    engine = GuardrailEngine(
        (
            FakeAdapter(
                "native",
                GuardrailDecision.MODIFY,
                calls,
                transform=lambda content: content.replace("original", "sanitized"),
            ),
            FakeAdapter("nemo", GuardrailDecision.ALLOW, calls),
        )
    )

    report = asyncio.run(engine.execute(request(nemo_enabled=True)))

    assert calls[1] == ("nemo", "sanitized content")
    assert report.final_decision is GuardrailDecision.MODIFY
    assert report.final_content == "sanitized content"
    assert report.should_continue is True


def test_engine_preserves_flags_and_all_adapter_evidence() -> None:
    calls: list[tuple[str, str]] = []
    engine = GuardrailEngine(
        (
            FakeAdapter("native", GuardrailDecision.FLAG, calls),
            FakeAdapter("nemo", GuardrailDecision.ALLOW, calls),
        )
    )

    report = asyncio.run(engine.execute(request(nemo_enabled=True)))

    assert report.final_decision is GuardrailDecision.FLAG
    assert report.should_continue is True
    assert len(report.adapter_results) == 2
    assert report.adapter_results[0].findings[0].code == "NATIVE_FINDING"


def test_engine_represents_adapter_failure_as_error_and_stops() -> None:
    calls: list[tuple[str, str]] = []
    engine = GuardrailEngine(
        (
            FakeAdapter("native", GuardrailDecision.ALLOW, calls, fail=True),
            FakeAdapter("nemo", GuardrailDecision.ALLOW, calls),
        )
    )

    report = asyncio.run(engine.execute(request(nemo_enabled=True)))

    assert calls == [("native", "original content")]
    assert report.final_decision is GuardrailDecision.ERROR
    assert report.final_content is None
    assert report.should_continue is False
    assert report.adapter_results[0].metadata == {"sanitized_error": True}
    assert "private adapter failure" not in report.model_dump_json()
