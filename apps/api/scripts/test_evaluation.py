import argparse
import asyncio
import json
import re
import sys
from typing import Any

from pydantic import ValidationError

from app.core.config import get_settings
from app.evaluation.blue import BlueEvaluator
from app.evaluation.contracts import (
    BlueEvaluationRequest,
    BlueEvaluationResult,
    EvaluationAttackPattern,
    EvaluationOutcome,
    EvaluationScenario,
    JudgeGenerationConfiguration,
    JudgeModelConfiguration,
    JudgeStructuredOutput,
)
from app.evaluation.exceptions import EvaluationError, JudgeOutputValidationError
from app.evaluation.judge import RubricJudge
from app.evaluation.output_parser import JudgeOutputParser
from app.evaluation.prompt_builder import MODEL_EVIDENCE_SOURCES
from app.evaluation.rubrics import get_rubric
from app.evaluation.service import EvaluationService
from app.guardrails.contracts import (
    GuardrailDecision,
    GuardrailExecutionReport,
    GuardrailStage,
)
from app.model_gateway.contracts import ModelGenerationResult
from app.model_gateway.dependencies import get_model_gateway
from app.reference_data import ATTACK_PATTERNS, SCENARIOS

MAX_DISPLAY_LENGTH = 2_000
_HF_TOKEN_PATTERN = re.compile(r"\bhf_[A-Za-z0-9_-]+\b")
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[^\s,;]+")
_CREDENTIAL_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|authorization|hf[_-]?token|"
    r"password|secret|token)\s*[:=]\s*['\"]?[^\s,'\";}]+"
)
_QUERY_URL_PATTERN = re.compile(r"https?://[^\s<>\"']*\?[^\s<>\"']*")
_THINK_PATTERN = re.compile(r"(?is)<think>.*?</think>")
_OPEN_THINK_PATTERN = re.compile(r"(?is)<think>.*$")
_REASONING_FIELD_PATTERN = re.compile(
    r'(?is)"(?:analysis|reasoning|chain_of_thought|private_reasoning)"\s*:\s*'
    r'"(?:\\.|[^"\\])*"'
)


def sanitize(value: object) -> str:
    content = str(value)
    token = get_settings().hf_token
    if token:
        content = content.replace(token, "[REDACTED]")
    content = _THINK_PATTERN.sub("[PRIVATE REASONING REDACTED]", content)
    content = _OPEN_THINK_PATTERN.sub("[PRIVATE REASONING REDACTED]", content)
    content = _REASONING_FIELD_PATTERN.sub(
        '"private_reasoning": "[REDACTED]"', content
    )
    content = _HF_TOKEN_PATTERN.sub("[REDACTED]", content)
    content = _BEARER_PATTERN.sub("Bearer [REDACTED]", content)
    content = _CREDENTIAL_PATTERN.sub(
        lambda match: f"{match.group(1)}=[REDACTED]", content
    )
    content = _QUERY_URL_PATTERN.sub("[URL WITH QUERY REDACTED]", content)
    if len(content) > MAX_DISPLAY_LENGTH:
        return f"{content[:MAX_DISPLAY_LENGTH]}... [TRUNCATED]"
    return content


class RecordingGateway:
    def __init__(self, gateway: Any) -> None:
        self._gateway = gateway
        self.call_count = 0
        self.result: ModelGenerationResult | None = None

    async def generate(self, model: Any, request: Any) -> ModelGenerationResult:
        self.call_count += 1
        self.result = await self._gateway.generate(model, request)
        return self.result


class RecordingJudgeOutputParser:
    def __init__(self) -> None:
        self._parser = JudgeOutputParser()
        self.raw_content: str | None = None
        self.json_result = "NOT RUN"
        self.schema_result = "NOT RUN"
        self.parsed_fields: dict[str, Any] = {}
        self.violations: list[str] = []
        self.output_shape = "unavailable"

    def parse(self, content: str) -> JudgeStructuredOutput:
        self.raw_content = content
        stripped = content.strip()
        self.output_shape = (
            "markdown-fenced JSON" if stripped.startswith("```") else "plain response"
        )
        try:
            candidate = self._parser._remove_json_fence(stripped)
        except JudgeOutputValidationError:
            self.json_result = "FAIL"
            self.violations.append("invalid Markdown fence envelope")
            raise

        try:
            decoded = json.loads(candidate)
        except json.JSONDecodeError:
            self.json_result = "FAIL"
            self.output_shape = (
                "explanatory text around JSON"
                if "{" in candidate and not candidate.lstrip().startswith("{")
                else "malformed or non-JSON response"
            )
            self.violations.append("JSON decoding failed")
            return self._parser.parse(content)

        self.json_result = "PASS"
        if isinstance(decoded, dict):
            self.parsed_fields = {
                key: decoded[key]
                for key in JudgeStructuredOutput.model_fields
                if key in decoded
            }
        try:
            JudgeStructuredOutput.model_validate(decoded)
        except ValidationError as exc:
            self.schema_result = "FAIL"
            for issue in exc.errors(include_input=False, include_url=False):
                field = ".".join(str(part) for part in issue["loc"]) or "root"
                kind = issue["type"]
                description = {
                    "missing": "missing field",
                    "extra_forbidden": "invalid field name",
                    "greater_than_equal": "out-of-range score/confidence",
                    "less_than_equal": "out-of-range score/confidence",
                    "enum": "invalid enum value",
                }.get(kind, f"wrong data type or invalid value ({kind})")
                self.violations.append(f"{description}: {field}")
        else:
            self.schema_result = "PASS"
        return self._parser.parse(content)


class RecordingRubricJudge(RubricJudge):
    def __init__(self, gateway: Any, output_parser: RecordingJudgeOutputParser) -> None:
        super().__init__(gateway, output_parser=output_parser)  # type: ignore[arg-type]
        self.semantic_result = "NOT RUN"
        self.semantic_violations: list[str] = []

    def _validate_output(
        self,
        output: JudgeStructuredOutput,
        request: BlueEvaluationRequest,
        blue_result: BlueEvaluationResult,
    ) -> None:
        try:
            super()._validate_output(output, request, blue_result)
        except JudgeOutputValidationError:
            self.semantic_result = "FAIL"
            if output.model_outcome is EvaluationOutcome.BLOCKED_BY_GUARDRAIL:
                self.semantic_violations.append("model_outcome cannot be blocked_by_guardrail")
            available = {
                item.code for item in blue_result.evidence
                if item.source in MODEL_EVIDENCE_SOURCES
            }
            self.semantic_violations.extend(
                f"invalid evidence reference: {sanitize(code)}"
                for code in output.evidence_codes
                if code not in available
            )
            raise
        self.semantic_result = "PASS"


def allowed_report(stage: GuardrailStage, content: str) -> GuardrailExecutionReport:
    return GuardrailExecutionReport(
        stage=stage,
        original_content=content,
        final_content=content,
        final_decision=GuardrailDecision.ALLOW,
        should_continue=True,
        adapter_results=(),
        total_latency_ms=0,
    )


def diagnostics(
    gateway: RecordingGateway,
    parser: RecordingJudgeOutputParser,
    judge: RecordingRubricJudge,
    *,
    status: str,
    failure_stage: str,
    error: str | None,
) -> dict[str, Any]:
    generation = gateway.result
    return {
        "status": status,
        "failure_stage": failure_stage,
        "sanitized_raw_judge_output": (
            sanitize(parser.raw_content) if parser.raw_content is not None else None
        ),
        "output_shape": parser.output_shape,
        "json_decoding": parser.json_result,
        "schema_validation": parser.schema_result,
        "semantic_contract_validation": judge.semantic_result,
        "parsed_keys": list(parser.parsed_fields),
        "parsed_fields": {
            key: sanitize(value) if isinstance(value, str) else value
            for key, value in parser.parsed_fields.items()
        },
        "violations": parser.violations + judge.semantic_violations,
        "latency_ms": generation.latency_ms if generation else None,
        "input_tokens": generation.input_tokens if generation else None,
        "output_tokens": generation.output_tokens if generation else None,
        "total_tokens": generation.total_tokens if generation else None,
        "external_model_calls": gateway.call_count,
        "sanitized_error": sanitize(error) if error else None,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Perform at most one explicit Judge Model evaluation request.",
    )
    parser.add_argument("judge_model_id", help="Canonical Judge Model identifier")
    parser.add_argument("--scenario", default="jailbreak")
    parser.add_argument("--attack-pattern", default="instruction_override")
    parser.add_argument("--attack-prompt", required=True)
    parser.add_argument("--target-response", required=True)
    parser.add_argument("--target-system-prompt")
    parser.add_argument("--provider-route", default="auto")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=800)
    parser.add_argument(
        "--guardrails-allow",
        action="store_true",
        help="Represent already-observed allow decisions without running guardrails",
    )
    return parser.parse_args()


async def run() -> int:
    arguments = parse_arguments()
    settings = get_settings()
    if not settings.hf_token:
        print("HF_TOKEN is required for real Judge Model inference.", file=sys.stderr)
        return 2

    scenario = next(
        (item for item in SCENARIOS if item.slug == arguments.scenario),
        None,
    )
    pattern = next(
        (item for item in ATTACK_PATTERNS if item.slug == arguments.attack_pattern),
        None,
    )
    if scenario is None or pattern is None:
        print("Unknown scenario or attack pattern.", file=sys.stderr)
        return 2

    request = BlueEvaluationRequest(
        scenario=EvaluationScenario(
            name=scenario.name,
            slug=scenario.slug,
            description=scenario.description,
        ),
        attack_pattern=EvaluationAttackPattern(
            name=pattern.name,
            slug=pattern.slug,
            description=pattern.description,
        ),
        attack_prompt=arguments.attack_prompt,
        target_response=arguments.target_response,
        target_was_called=True,
        target_system_prompt=arguments.target_system_prompt,
        input_guardrail_report=(
            allowed_report(GuardrailStage.INPUT, arguments.attack_prompt)
            if arguments.guardrails_allow else None
        ),
        output_guardrail_report=(
            allowed_report(GuardrailStage.OUTPUT, arguments.target_response)
            if arguments.guardrails_allow else None
        ),
        turn_number=1,
    )
    judge_model = JudgeModelConfiguration(
        canonical_model_id=arguments.judge_model_id,
        provider="huggingface",
        third_party=True,
        provider_configuration={"provider_route": arguments.provider_route},
        generation=JudgeGenerationConfiguration(
            temperature=arguments.temperature,
            max_tokens=arguments.max_tokens,
        ),
    )
    gateway = RecordingGateway(get_model_gateway())
    output_parser = RecordingJudgeOutputParser()
    judge = RecordingRubricJudge(gateway, output_parser)
    service = EvaluationService(BlueEvaluator(), judge)
    rubric = get_rubric(scenario.slug)
    try:
        result = await service.evaluate(request, judge_model)
    except EvaluationError as exc:
        if gateway.result is None:
            stage = "model/provider generation failure"
        elif output_parser.json_result == "FAIL":
            stage = "JSON decoding failure"
        elif output_parser.schema_result == "FAIL":
            stage = "schema/Pydantic validation failure"
        elif judge.semantic_result == "FAIL":
            stage = "semantic/contract validation failure"
        else:
            stage = "other post-generation failure"
        report = diagnostics(
            gateway, output_parser, judge,
            status="FAIL", failure_stage=stage, error=str(exc),
        )
        report.update({"rubric_id": rubric.rubric_id, "rubric_version": rubric.version})
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    report = diagnostics(
        gateway, output_parser, judge,
        status="PASS", failure_stage="successful judge result", error=None,
    )
    report.update({
        "rubric_id": result.rubric_id,
        "rubric_version": result.rubric_version,
        "model_outcome": result.model_outcome.value if result.model_outcome else None,
        "system_outcome": result.system_outcome.value,
    })
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
