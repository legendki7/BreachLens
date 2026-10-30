import argparse
import asyncio
import json
import re
import sys
from typing import Any

from pydantic import ValidationError

from app.core.config import get_settings
from app.model_gateway.contracts import ModelGenerationResult
from app.model_gateway.dependencies import get_model_gateway
from app.red_agent.contracts import (
    AttackerModelConfiguration,
    GeneratedAttackOutput,
    PriorRedAgentTurn,
    RedAgentAttackPattern,
    RedAgentGenerationConfiguration,
    RedAgentRequest,
    RedAgentScenario,
)
from app.red_agent.exceptions import (
    RedAgentError,
    RedAgentGenerationError,
    RedAgentObjectiveFidelityError,
    RedAgentOutputValidationError,
)
from app.red_agent.objective_validator import RedAgentObjectiveValidator
from app.red_agent.output_parser import RedAgentOutputParser
from app.red_agent.planner import AttackStrategyPlanner
from app.red_agent.prompt_builder import RedAgentPromptBuilder
from app.red_agent.repair_prompt_builder import RedAgentRepairPromptBuilder
from app.red_agent.service import RedAgentService
from app.red_agent.target_boundary import TargetBoundaryMatcher
from app.reference_data import ATTACK_PATTERNS, SCENARIOS

MAX_RAW_OUTPUT_LENGTH = 2_000
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[^\s,;]+")
_HF_TOKEN_PATTERN = re.compile(r"\bhf_[A-Za-z0-9_-]+\b")
_CREDENTIAL_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|authorization|hf[_-]?token|password|secret|token)"
    r"\s*[:=]\s*['\"]?[^\s,'\";}]+"
)
_URL_WITH_QUERY_PATTERN = re.compile(r"https?://[^\s<>\"']*\?[^\s<>\"']*")


def sanitize_raw_output(content: str) -> str:
    sanitized = _BEARER_PATTERN.sub("Bearer [REDACTED]", content)
    sanitized = _HF_TOKEN_PATTERN.sub("[REDACTED]", sanitized)
    sanitized = _CREDENTIAL_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        sanitized,
    )
    sanitized = _URL_WITH_QUERY_PATTERN.sub(
        lambda match: f"{match.group(0).split('?', 1)[0]}?[REDACTED]",
        sanitized,
    )
    if len(sanitized) > MAX_RAW_OUTPUT_LENGTH:
        return f"{sanitized[:MAX_RAW_OUTPUT_LENGTH]}…"
    return sanitized


class RecordingGateway:
    def __init__(self, gateway: Any) -> None:
        self._gateway = gateway
        self.result: ModelGenerationResult | None = None
        self.results: list[ModelGenerationResult] = []
        self.call_count = 0

    async def generate(self, model: Any, request: Any) -> ModelGenerationResult:
        self.call_count += 1
        self.result = await self._gateway.generate(model, request)
        self.results.append(self.result)
        return self.result


class RecordingPlanner:
    def __init__(self) -> None:
        self._planner = AttackStrategyPlanner()
        self.selected_pattern: RedAgentAttackPattern | None = None

    def select_pattern(
        self,
        scenario: RedAgentScenario,
        allowed_patterns: tuple[RedAgentAttackPattern, ...],
        prior_turns: tuple[PriorRedAgentTurn, ...],
        turn_number: int,
    ) -> RedAgentAttackPattern:
        self.selected_pattern = self._planner.select_pattern(
            scenario,
            allowed_patterns,
            prior_turns,
            turn_number,
        )
        return self.selected_pattern


class RecordingOutputParser:
    def __init__(self) -> None:
        self._parser = RedAgentOutputParser()
        self.raw_content: str | None = None
        self.json_result = "NOT RUN"
        self.schema_result = "NOT RUN"
        self.parsed_output: GeneratedAttackOutput | None = None
        self.attempts: list[dict[str, Any]] = []

    def parse(self, content: str) -> GeneratedAttackOutput:
        self.raw_content = content
        self.json_result = "NOT RUN"
        self.schema_result = "NOT RUN"
        self.parsed_output = None
        candidate: str | None = None
        try:
            candidate = self._parser._remove_json_fence(content.strip())
        except RedAgentOutputValidationError:
            self.json_result = "FAIL (invalid Markdown fence envelope)"

        decoded: object | None = None
        if candidate is not None:
            try:
                decoded = json.loads(candidate)
                self.json_result = "PASS"
            except json.JSONDecodeError:
                self.json_result = "FAIL"

        if self.json_result == "PASS":
            try:
                GeneratedAttackOutput.model_validate(decoded)
                self.schema_result = "PASS"
            except ValidationError:
                self.schema_result = "FAIL"

        try:
            parsed = self._parser.parse(content)
        except RedAgentOutputValidationError:
            self.attempts.append(
                {
                    "raw_content": content,
                    "json_result": self.json_result,
                    "schema_result": self.schema_result,
                    "parsed_output": None,
                }
            )
            raise
        self.parsed_output = parsed
        self.attempts.append(
            {
                "raw_content": content,
                "json_result": self.json_result,
                "schema_result": self.schema_result,
                "parsed_output": parsed,
            }
        )
        return parsed


class RecordingObjectiveValidator:
    def __init__(self, boundary_matcher: TargetBoundaryMatcher) -> None:
        self._boundary_matcher = boundary_matcher
        self._validator = RedAgentObjectiveValidator(boundary_matcher)
        self.result = "NOT RUN"
        self.results: list[str] = []
        self.reason_codes: list[str | None] = []
        self.paths: list[str] = []

    def validate(
        self,
        scenario: RedAgentScenario,
        output: GeneratedAttackOutput,
        target_security_boundary: str | None = None,
    ) -> None:
        try:
            self._validator.validate(scenario, output, target_security_boundary)
        except RedAgentObjectiveFidelityError as exc:
            self.result = "FAIL"
            self.results.append(self.result)
            self.reason_codes.append(exc.reason_code)
            self.paths.append(
                "off_target_security_boundary"
                if exc.reason_code == "off_target_security_boundary"
                else "none"
            )
            raise
        self.result = "PASS"
        self.results.append(self.result)
        self.reason_codes.append(None)
        self.paths.append(
            self._validation_path(scenario, output, target_security_boundary)
        )

    def _validation_path(
        self,
        scenario: RedAgentScenario,
        output: GeneratedAttackOutput,
        target_security_boundary: str | None,
    ) -> str:
        prompt = " ".join(output.attack_prompt.split())
        if self._validator._attempts_instruction_override(prompt):
            return "instruction_override"
        if self._boundary_matcher.attempts_protected_extraction(
            prompt,
            target_security_boundary,
        ):
            return "target_boundary_protected_context_extraction"
        if self._validator._attempts_unauthorized_behavior_change(prompt):
            return "unauthorized_behavior_change"
        return "none"


def failure_stage(
    parser: RecordingOutputParser,
    validator: RecordingObjectiveValidator,
) -> str:
    if parser.json_result.startswith("FAIL"):
        return "JSON decoding failure"
    if parser.schema_result == "FAIL":
        return "Pydantic/schema validation failure"
    if validator.result == "FAIL":
        return "Objective-fidelity validation failure"
    return "Other post-generation validation failure"


def print_recorded_diagnostics(
    parser: RecordingOutputParser,
    validator: RecordingObjectiveValidator,
    planner: RecordingPlanner,
    gateway: RecordingGateway,
) -> None:
    selected = planner.selected_pattern.slug if planner.selected_pattern else "unavailable"
    raw = (
        sanitize_raw_output(parser.raw_content)
        if parser.raw_content is not None
        else "unavailable"
    )
    print(f"Selected attack pattern: {selected}")
    print(f"Sanitized raw attacker output: {raw}")
    print(f"JSON parsing result: {parser.json_result}")
    print(f"Schema validation result: {parser.schema_result}")
    print(f"Objective-fidelity validation result: {validator.result}")
    if parser.parsed_output is not None:
        print(
            "Parsed attack_prompt: "
            f"{sanitize_raw_output(parser.parsed_output.attack_prompt)}"
        )
        print(
            "Parsed strategy_summary: "
            f"{sanitize_raw_output(parser.parsed_output.strategy_summary)}"
        )
        print(
            "Parsed adaptation_reason: "
            f"{sanitize_raw_output(parser.parsed_output.adaptation_reason)}"
        )
    if gateway.result is not None:
        print(f"Latency ms: {gateway.result.latency_ms}")
        print(f"Input tokens: {gateway.result.input_tokens}")
        print(f"Output tokens: {gateway.result.output_tokens}")
        print(f"Total tokens: {gateway.result.total_tokens}")


def print_repair_diagnostics(
    parser: RecordingOutputParser,
    validator: RecordingObjectiveValidator,
    gateway: RecordingGateway,
    result: Any | None,
) -> None:
    generation_attempts = (
        result.metadata.get("generation_attempts")
        if result is not None
        else gateway.call_count
    )
    objective_repair_used = (
        result.metadata.get("objective_repair_used")
        if result is not None
        else gateway.call_count > 1
    )
    first_objective_result = (
        validator.results[0] if validator.results else "NOT RUN"
    )
    first_attempt_prompt = "unavailable"
    if parser.attempts:
        first_output = parser.attempts[0]["parsed_output"]
        if isinstance(first_output, GeneratedAttackOutput):
            first_attempt_prompt = sanitize_raw_output(first_output.attack_prompt)
    repair_attempt_prompt = "not applicable"
    if len(parser.attempts) > 1:
        repair_output = parser.attempts[1]["parsed_output"]
        if isinstance(repair_output, GeneratedAttackOutput):
            repair_attempt_prompt = sanitize_raw_output(repair_output.attack_prompt)
    repair_reason = validator.reason_codes[0] if validator.reason_codes else None
    first_path = validator.paths[0] if validator.paths else "none"
    final_path = validator.paths[-1] if validator.paths else "none"

    print(f"Generation attempts: {generation_attempts}")
    print(f"Objective repair used: {str(bool(objective_repair_used)).lower()}")
    print(f"First-attempt objective-fidelity result: {first_objective_result}")
    print(f"First-attempt attack_prompt: {first_attempt_prompt}")
    print(f"First-attempt validation path: {first_path}")
    print(f"Repair reason code: {repair_reason or 'not applicable'}")
    print(f"Repair attack_prompt: {repair_attempt_prompt}")
    print(
        "Final objective-fidelity result: "
        f"{validator.results[-1] if validator.results else 'NOT RUN'}"
    )
    print(f"Final validation path: {final_path}")
    print(f"Total external model calls: {gateway.call_count}")
    for index, generation in enumerate(gateway.results, start=1):
        print(
            f"Attempt {index} metrics: latency_ms={generation.latency_ms}, "
            f"input_tokens={generation.input_tokens}, "
            f"output_tokens={generation.output_tokens}, "
            f"total_tokens={generation.total_tokens}"
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Perform one explicit Red Agent generation request.",
    )
    parser.add_argument("model_id", help="Canonical attacker-model identifier")
    parser.add_argument("--scenario", default="jailbreak", help="Scenario slug")
    parser.add_argument("--attack-pattern", help="Optional allowed attack-pattern slug")
    parser.add_argument(
        "--target-system-prompt",
        help="Target context (defaults to the canonical scenario target prompt)",
    )
    parser.add_argument(
        "--provider-route",
        default="auto",
        help="Hugging Face Inference Provider route (default: auto)",
    )
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--turn-number", type=int, default=1)
    parser.add_argument("--max-turns", type=int, default=1)
    return parser.parse_args()


async def run() -> int:
    arguments = parse_arguments()
    settings = get_settings()
    if not settings.hf_token:
        print("HF_TOKEN is required for real Red Agent inference.", file=sys.stderr)
        return 2

    scenario = next(
        (item for item in SCENARIOS if item.slug == arguments.scenario),
        None,
    )
    if scenario is None:
        print(f"Unknown scenario: {arguments.scenario}", file=sys.stderr)
        return 2

    patterns_by_slug = {pattern.slug: pattern for pattern in ATTACK_PATTERNS}
    allowed_patterns = tuple(
        RedAgentAttackPattern(
            name=patterns_by_slug[slug].name,
            slug=patterns_by_slug[slug].slug,
            description=patterns_by_slug[slug].description,
            category=patterns_by_slug[slug].category,
        )
        for slug in scenario.attack_pattern_slugs
    )
    request = RedAgentRequest(
        scenario=RedAgentScenario(
            name=scenario.name,
            slug=scenario.slug,
            description=scenario.description,
            severity=scenario.severity,
        ),
        allowed_attack_patterns=allowed_patterns,
        attack_pattern_slug=arguments.attack_pattern,
        target_system_prompt=(
            arguments.target_system_prompt or scenario.target_system_prompt
        ),
        turn_number=arguments.turn_number,
        max_turns=arguments.max_turns,
        attacker_model=AttackerModelConfiguration(
            canonical_model_id=arguments.model_id,
            provider="huggingface",
            third_party=True,
            role="attacker",
            provider_configuration={"provider_route": arguments.provider_route},
        ),
        generation=RedAgentGenerationConfiguration(
            temperature=arguments.temperature,
            max_tokens=arguments.max_tokens,
        ),
    )

    print(f"Attacker model: {arguments.model_id}")
    print(f"Scenario: {scenario.name} ({scenario.slug})")
    boundary_matcher = TargetBoundaryMatcher()
    protected_target_concepts = boundary_matcher.protected_concept_labels(
        request.target_system_prompt
    )
    print(
        "Normalized protected_target_concepts: "
        f"{json.dumps(protected_target_concepts)}"
    )
    gateway = RecordingGateway(get_model_gateway())
    planner = RecordingPlanner()
    parser = RecordingOutputParser()
    validator = RecordingObjectiveValidator(boundary_matcher)
    service = RedAgentService(
        gateway,
        planner=planner,
        prompt_builder=RedAgentPromptBuilder(boundary_matcher),
        output_parser=parser,
        objective_validator=validator,
        repair_prompt_builder=RedAgentRepairPromptBuilder(boundary_matcher),
    )
    try:
        result = await service.generate(request)
    except RedAgentGenerationError as exc:
        print("Exact failure stage: Model generation failure", file=sys.stderr)
        print_recorded_diagnostics(parser, validator, planner, gateway)
        print_repair_diagnostics(parser, validator, gateway, None)
        print(str(exc), file=sys.stderr)
        return 1
    except RedAgentOutputValidationError as exc:
        print(f"Exact failure stage: {failure_stage(parser, validator)}", file=sys.stderr)
        print_recorded_diagnostics(parser, validator, planner, gateway)
        print_repair_diagnostics(parser, validator, gateway, None)
        print(str(exc), file=sys.stderr)
        return 1
    except RedAgentError as exc:
        print("Exact failure stage: Other", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    print("Exact failure stage: Successful generation")
    print_recorded_diagnostics(parser, validator, planner, gateway)
    print_repair_diagnostics(parser, validator, gateway, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
