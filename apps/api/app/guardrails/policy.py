from dataclasses import dataclass
from enum import StrEnum

from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailFindingSeverity,
    GuardrailPolicyContext,
    GuardrailResult,
)
from app.guardrails.exceptions import GuardrailConfigurationError

NATIVE_ADAPTER = "native"
NEMO_ADAPTER = "nemo"
EXPLICIT_CRITICAL_NATIVE_RULES = frozenset(
    {"RTA_INPUT_SYSTEM_CONTEXT_EXTRACTION"}
)


class PolicyStrictness(StrEnum):
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


@dataclass(frozen=True, slots=True)
class GuardrailPolicyBehavior:
    strictness: PolicyStrictness
    enabled_adapters: tuple[str, ...]


class GuardrailPolicyResolver:
    """Translate project profiles into Phase 6 enforcement behavior."""

    def resolve(
        self,
        profile: GuardrailPolicyContext,
    ) -> GuardrailPolicyBehavior:
        try:
            strictness = PolicyStrictness(profile.strictness_level.strip().lower())
        except ValueError as exc:
            raise GuardrailConfigurationError(
                "Unsupported policy strictness level"
            ) from exc

        nemo_enabled = profile.configuration.get("nemo_enabled", False)
        if not isinstance(nemo_enabled, bool):
            raise GuardrailConfigurationError(
                "nemo_enabled policy configuration must be a boolean"
            )
        adapters = (NATIVE_ADAPTER, NEMO_ADAPTER) if nemo_enabled else (NATIVE_ADAPTER,)
        return GuardrailPolicyBehavior(
            strictness=strictness,
            enabled_adapters=adapters,
        )

    def enforce(
        self,
        result: GuardrailResult,
        behavior: GuardrailPolicyBehavior,
    ) -> GuardrailResult:
        if result.decision is not GuardrailDecision.BLOCK:
            return result
        if behavior.strictness is PolicyStrictness.STRICT:
            return result
        if behavior.strictness is PolicyStrictness.MODERATE:
            enforce_block = any(
                finding.severity is GuardrailFindingSeverity.CRITICAL
                and finding.confidence is not None
                and finding.confidence >= 0.8
                for finding in result.findings
            )
        else:
            enforce_block = result.adapter == NATIVE_ADAPTER and any(
                finding.code in EXPLICIT_CRITICAL_NATIVE_RULES
                and finding.severity is GuardrailFindingSeverity.CRITICAL
                and finding.confidence is not None
                and finding.confidence >= 0.95
                for finding in result.findings
            )

        if enforce_block:
            return result
        return result.model_copy(
            update={
                "decision": GuardrailDecision.FLAG,
                "processed_content": result.original_content,
                "metadata": {
                    **result.metadata,
                    "policy_downgraded_block_to_flag": True,
                    "policy_strictness": behavior.strictness.value,
                },
            }
        )
