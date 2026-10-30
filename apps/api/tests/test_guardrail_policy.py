from uuid import uuid4

from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailFinding,
    GuardrailFindingSeverity,
    GuardrailPolicyContext,
    GuardrailResult,
    GuardrailStage,
)
from app.guardrails.policy import GuardrailPolicyResolver, PolicyStrictness
from app.models.policies import PolicyProfile


def profile(level: str, *, nemo_enabled: bool = False) -> GuardrailPolicyContext:
    return GuardrailPolicyContext(
        name=level.title(),
        slug=level,
        strictness_level=level,
        configuration={"nemo_enabled": nemo_enabled},
    )


def blocked_result(
    severity: GuardrailFindingSeverity,
    confidence: float,
    *,
    adapter: str = "native",
    code: str = "RTA_INPUT_INSTRUCTION_OVERRIDE",
) -> GuardrailResult:
    return GuardrailResult(
        stage=GuardrailStage.INPUT,
        decision=GuardrailDecision.BLOCK,
        original_content="content",
        processed_content=None,
        triggered_rules=(code,),
        findings=(
            GuardrailFinding(
                code=code,
                name="Finding",
                severity=severity,
                description="Structured heuristic finding.",
                confidence=confidence,
            ),
        ),
        adapter=adapter,
        latency_ms=1,
    )


def test_policy_resolver_supports_profiles_and_configured_nemo() -> None:
    resolver = GuardrailPolicyResolver()

    strict = resolver.resolve(profile("strict", nemo_enabled=True))
    moderate = resolver.resolve(profile("moderate"))
    permissive = resolver.resolve(profile("permissive"))

    assert strict.strictness is PolicyStrictness.STRICT
    assert strict.enabled_adapters == ("native", "nemo")
    assert moderate.strictness is PolicyStrictness.MODERATE
    assert moderate.enabled_adapters == ("native",)
    assert permissive.strictness is PolicyStrictness.PERMISSIVE


def test_policy_context_translates_existing_policy_profile_record() -> None:
    record = PolicyProfile(
        id=uuid4(),
        name="Strict",
        slug="strict",
        description="Strict Phase 6 runtime profile.",
        strictness_level="strict",
        configuration={"nemo_enabled": True},
        is_builtin=True,
        is_active=True,
    )

    context = GuardrailPolicyContext.from_policy_profile(record)
    behavior = GuardrailPolicyResolver().resolve(context)

    assert context.id == record.id
    assert behavior.strictness is PolicyStrictness.STRICT
    assert behavior.enabled_adapters == ("native", "nemo")


def test_strict_enforces_adapter_blocks() -> None:
    resolver = GuardrailPolicyResolver()
    result = blocked_result(GuardrailFindingSeverity.HIGH, 0.9)

    enforced = resolver.enforce(result, resolver.resolve(profile("strict")))

    assert enforced.decision is GuardrailDecision.BLOCK


def test_moderate_blocks_only_high_confidence_critical_findings() -> None:
    resolver = GuardrailPolicyResolver()
    behavior = resolver.resolve(profile("moderate"))

    lower = resolver.enforce(
        blocked_result(GuardrailFindingSeverity.HIGH, 0.9),
        behavior,
    )
    critical = resolver.enforce(
        blocked_result(GuardrailFindingSeverity.CRITICAL, 0.9),
        behavior,
    )

    assert lower.decision is GuardrailDecision.FLAG
    assert lower.processed_content == "content"
    assert critical.decision is GuardrailDecision.BLOCK


def test_permissive_only_blocks_explicit_critical_native_condition() -> None:
    resolver = GuardrailPolicyResolver()
    behavior = resolver.resolve(profile("permissive"))
    generic_critical = blocked_result(
        GuardrailFindingSeverity.CRITICAL,
        0.99,
        adapter="nemo",
        code="NEMO_RAIL_BLOCKED",
    )
    explicit_native = blocked_result(
        GuardrailFindingSeverity.CRITICAL,
        0.98,
        code="RTA_INPUT_SYSTEM_CONTEXT_EXTRACTION",
    )

    observed = resolver.enforce(generic_critical, behavior)
    blocked = resolver.enforce(explicit_native, behavior)

    assert observed.decision is GuardrailDecision.FLAG
    assert blocked.decision is GuardrailDecision.BLOCK


def test_existing_flags_are_preserved_across_profiles() -> None:
    resolver = GuardrailPolicyResolver()
    flagged = blocked_result(
        GuardrailFindingSeverity.HIGH,
        0.7,
    ).model_copy(
        update={
            "decision": GuardrailDecision.FLAG,
            "processed_content": "content",
        }
    )

    for level in ("strict", "moderate", "permissive"):
        result = resolver.enforce(flagged, resolver.resolve(profile(level)))
        assert result.decision is GuardrailDecision.FLAG
        assert result.findings == flagged.findings
