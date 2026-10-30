import asyncio
from enum import StrEnum
from types import SimpleNamespace

import nemoguardrails
import pytest

from app.guardrails.adapters.nemo import NeMoGuardrailAdapter
from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailPolicyContext,
    GuardrailRequest,
    GuardrailScenarioContext,
    GuardrailStage,
)
from app.guardrails.exceptions import GuardrailExecutionError


class FakeStatus(StrEnum):
    PASSED = "passed"
    MODIFIED = "modified"
    BLOCKED = "blocked"


class FakeRails:
    def __init__(self, response: object | None = None, *, fail: bool = False) -> None:
        self.response = response
        self.fail = fail
        self.calls: list[tuple[list[dict[str, str]], list[object] | None]] = []

    async def check_async(
        self,
        messages: list[dict[str, str]],
        rail_types: list[object] | None = None,
    ) -> object:
        self.calls.append((messages, rail_types))
        if self.fail:
            raise RuntimeError("private NeMo failure")
        return self.response


def request(stage: GuardrailStage) -> GuardrailRequest:
    return GuardrailRequest(
        stage=stage,
        content="content under review",
        scenario=GuardrailScenarioContext(
            name="Jailbreak",
            slug="jailbreak",
            description="Test instruction bypass.",
        ),
        policy_profile=GuardrailPolicyContext(
            name="Strict",
            slug="strict",
            strictness_level="strict",
            configuration={"nemo_enabled": True},
        ),
    )


def test_nemo_dependency_imports_at_the_pinned_version() -> None:
    assert nemoguardrails.__version__ == "0.23.0"


def test_nemo_adapter_executes_and_normalizes_input_stage() -> None:
    rails = FakeRails(SimpleNamespace(status=FakeStatus.PASSED, content="content under review", rail=None))
    adapter = NeMoGuardrailAdapter(
        rails=rails,
        rail_type_factory=lambda value: f"rail:{value}",
    )

    result = asyncio.run(adapter.apply(request(GuardrailStage.INPUT)))

    assert rails.calls == [
        ([{"role": "user", "content": "content under review"}], ["rail:input"])
    ]
    assert result.decision is GuardrailDecision.ALLOW
    assert result.processed_content == "content under review"


def test_nemo_adapter_executes_and_normalizes_output_stage() -> None:
    rails = FakeRails(
        SimpleNamespace(
            status=FakeStatus.BLOCKED,
            content="guardrail refusal",
            rail="red team arena output rail",
        )
    )
    adapter = NeMoGuardrailAdapter(
        rails=rails,
        rail_type_factory=lambda value: f"rail:{value}",
    )

    result = asyncio.run(adapter.apply(request(GuardrailStage.OUTPUT)))

    assert rails.calls[0][0][0]["role"] == "assistant"
    assert rails.calls[0][1] == ["rail:output"]
    assert result.decision is GuardrailDecision.BLOCK
    assert result.processed_content is None
    assert result.triggered_rules == ("red team arena output rail",)
    assert result.findings[0].code == "NEMO_RAIL_BLOCKED"


def test_nemo_adapter_normalizes_modified_content() -> None:
    rails = FakeRails(
        SimpleNamespace(
            status=FakeStatus.MODIFIED,
            content="sanitized content",
            rail="red team arena input rail",
        )
    )
    adapter = NeMoGuardrailAdapter(rails=rails)

    result = asyncio.run(adapter.apply(request(GuardrailStage.INPUT)))

    assert result.decision is GuardrailDecision.MODIFY
    assert result.processed_content == "sanitized content"


def test_nemo_adapter_converts_failures_without_exposing_details() -> None:
    adapter = NeMoGuardrailAdapter(rails=FakeRails(fail=True))

    with pytest.raises(GuardrailExecutionError) as captured:
        asyncio.run(adapter.apply(request(GuardrailStage.INPUT)))

    assert str(captured.value) == "Guardrail execution failed"
    assert "private NeMo failure" not in str(captured.value)
