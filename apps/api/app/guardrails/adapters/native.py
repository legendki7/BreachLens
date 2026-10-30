import re
from dataclasses import dataclass
from time import perf_counter

from app.guardrails.adapter import GuardrailAdapter
from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailFinding,
    GuardrailFindingSeverity,
    GuardrailRequest,
    GuardrailResult,
    GuardrailStage,
)


@dataclass(frozen=True, slots=True)
class NativeRule:
    code: str
    name: str
    pattern: re.Pattern[str]
    severity: GuardrailFindingSeverity
    confidence: float
    description: str
    evidence_summary: str


INPUT_RULES = (
    NativeRule(
        code="RTA_INPUT_SYSTEM_CONTEXT_EXTRACTION",
        name="Possible hidden-context extraction request",
        pattern=re.compile(
            r"\b(?:reveal|show|print|repeat|provide|display|expose)\b.{0,50}"
            r"\b(?:system prompt|hidden instructions?|developer instructions?|"
            r"internal instructions?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
        severity=GuardrailFindingSeverity.CRITICAL,
        confidence=0.98,
        description=(
            "The input matches a narrow phrase pattern associated with requests for "
            "protected system or hidden context."
        ),
        evidence_summary="A disclosure verb appeared near a protected-context phrase.",
    ),
    NativeRule(
        code="RTA_INPUT_INSTRUCTION_OVERRIDE",
        name="Possible instruction override",
        pattern=re.compile(
            r"\b(?:ignore|disregard|forget|override)\b.{0,40}"
            r"\b(?:previous|prior|system|developer|all)\b.{0,30}"
            r"\binstructions?\b",
            re.IGNORECASE | re.DOTALL,
        ),
        severity=GuardrailFindingSeverity.HIGH,
        confidence=0.9,
        description=(
            "The input matches a narrow explicit instruction-override phrase; this is "
            "a heuristic finding, not proof of a successful attack."
        ),
        evidence_summary="An override verb appeared near a prior-instruction reference.",
    ),
)

OUTPUT_RULES = (
    NativeRule(
        code="RTA_OUTPUT_SYSTEM_CONTEXT_MARKER",
        name="Possible protected-context disclosure marker",
        pattern=re.compile(
            r"\b(?:system prompt|hidden instructions?|developer message)\s*[:=]",
            re.IGNORECASE,
        ),
        severity=GuardrailFindingSeverity.HIGH,
        confidence=0.85,
        description=(
            "The output contains a marker sometimes used when reproducing protected "
            "context; manual or future evaluator review is required."
        ),
        evidence_summary="A protected-context label appeared in the output.",
    ),
    NativeRule(
        code="RTA_OUTPUT_SECRET_LIKE_MATERIAL",
        name="Possible secret-like material",
        pattern=re.compile(
            r"\b(?:sk-|hf_)[A-Za-z0-9_-]{16,}\b|"
            r"\bBearer\s+[A-Za-z0-9._-]{16,}",
            re.IGNORECASE,
        ),
        severity=GuardrailFindingSeverity.CRITICAL,
        confidence=0.8,
        description=(
            "The output resembles a token format. Pattern matching alone does not "
            "establish that the value is real or sensitive."
        ),
        evidence_summary="A token-like prefix and length pattern appeared in the output.",
    ),
)


class NativeGuardrailAdapter(GuardrailAdapter):
    name = "native"

    async def apply(self, request: GuardrailRequest) -> GuardrailResult:
        started_at = perf_counter()
        rules = INPUT_RULES if request.stage is GuardrailStage.INPUT else OUTPUT_RULES
        matched_rules = tuple(rule for rule in rules if rule.pattern.search(request.content))
        findings = tuple(self._finding(rule) for rule in matched_rules)

        if not findings:
            decision = GuardrailDecision.ALLOW
        elif request.stage is GuardrailStage.INPUT:
            decision = GuardrailDecision.BLOCK
        else:
            decision = GuardrailDecision.FLAG

        return GuardrailResult(
            stage=request.stage,
            decision=decision,
            original_content=request.content,
            processed_content=(
                None if decision is GuardrailDecision.BLOCK else request.content
            ),
            triggered_rules=tuple(rule.code for rule in matched_rules),
            findings=findings,
            adapter=self.name,
            latency_ms=(perf_counter() - started_at) * 1000,
            metadata={"deterministic": True, "conclusive_breach": False},
        )

    @staticmethod
    def _finding(rule: NativeRule) -> GuardrailFinding:
        return GuardrailFinding(
            code=rule.code,
            name=rule.name,
            severity=rule.severity,
            description=rule.description,
            confidence=rule.confidence,
            evidence_summary=rule.evidence_summary,
        )
