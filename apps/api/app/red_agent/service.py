from collections.abc import Mapping
from typing import Any

from app.model_gateway.contracts import ModelGenerationResult
from app.model_gateway.exceptions import ModelGatewayError
from app.model_gateway.gateway import ModelGateway
from app.red_agent.contracts import (
    RedAgentAttackPattern,
    RedAgentRequest,
    RedAgentResult,
)
from app.red_agent.exceptions import (
    InvalidAttackPatternError,
    RedAgentGenerationError,
    RedAgentObjectiveFidelityError,
)
from app.red_agent.output_parser import RedAgentOutputParser
from app.red_agent.objective_validator import RedAgentObjectiveValidator
from app.red_agent.planner import AttackStrategyPlanner
from app.red_agent.prompt_builder import RedAgentPromptBuilder
from app.red_agent.repair_prompt_builder import RedAgentRepairPromptBuilder
from app.red_agent.runtime import build_attacker_gateway_model
from app.red_agent.target_boundary import TargetBoundaryMatcher


class RedAgentService:
    def __init__(
        self,
        gateway: ModelGateway,
        planner: AttackStrategyPlanner | None = None,
        prompt_builder: RedAgentPromptBuilder | None = None,
        output_parser: RedAgentOutputParser | None = None,
        objective_validator: RedAgentObjectiveValidator | None = None,
        repair_prompt_builder: RedAgentRepairPromptBuilder | None = None,
    ) -> None:
        boundary_matcher = TargetBoundaryMatcher()
        self._gateway = gateway
        self._planner = planner or AttackStrategyPlanner()
        self._prompt_builder = prompt_builder or RedAgentPromptBuilder(boundary_matcher)
        self._output_parser = output_parser or RedAgentOutputParser()
        self._objective_validator = objective_validator or RedAgentObjectiveValidator(
            boundary_matcher
        )
        self._repair_prompt_builder = repair_prompt_builder or RedAgentRepairPromptBuilder(
            boundary_matcher
        )

    async def generate(self, request: RedAgentRequest) -> RedAgentResult:
        selected_pattern = self._select_pattern(request)
        generation_request = self._prompt_builder.build(request, selected_pattern)
        attacker_model = build_attacker_gateway_model(request.attacker_model)

        generation = await self._generate(attacker_model, generation_request)

        structured_output = self._output_parser.parse(generation.content)
        generation_attempts = 1
        objective_repair_used = False
        try:
            self._objective_validator.validate(
                request.scenario,
                structured_output,
                request.target_system_prompt,
            )
        except RedAgentObjectiveFidelityError as failure:
            objective_repair_used = True
            generation_attempts = 2
            repair_request = self._repair_prompt_builder.build(
                request,
                selected_pattern,
                structured_output,
                failure,
            )
            generation = await self._generate(attacker_model, repair_request)
            structured_output = self._output_parser.parse(generation.content)
            self._objective_validator.validate(
                request.scenario,
                structured_output,
                request.target_system_prompt,
            )

        return self._normalize_result(
            request,
            selected_pattern,
            generation,
            structured_output.attack_prompt,
            structured_output.strategy_summary,
            structured_output.adaptation_reason,
            generation_attempts,
            objective_repair_used,
        )

    async def _generate(
        self,
        attacker_model: Any,
        generation_request: Any,
    ) -> ModelGenerationResult:
        try:
            return await self._gateway.generate(attacker_model, generation_request)
        except ModelGatewayError as exc:
            raise RedAgentGenerationError(exc.provider_type) from exc

    def _select_pattern(self, request: RedAgentRequest) -> RedAgentAttackPattern:
        if request.attack_pattern_slug is None:
            return self._planner.select_pattern(
                request.scenario,
                request.allowed_attack_patterns,
                request.prior_turns,
                request.turn_number,
            )

        for pattern in request.allowed_attack_patterns:
            if pattern.slug == request.attack_pattern_slug:
                return pattern
        raise InvalidAttackPatternError(
            request.attack_pattern_slug,
            request.scenario.slug,
        )

    @staticmethod
    def _normalize_result(
        request: RedAgentRequest,
        selected_pattern: RedAgentAttackPattern,
        generation: ModelGenerationResult,
        attack_prompt: str,
        strategy_summary: str,
        adaptation_reason: str,
        generation_attempts: int,
        objective_repair_used: bool,
    ) -> RedAgentResult:
        return RedAgentResult(
            scenario_slug=request.scenario.slug,
            attack_prompt=attack_prompt,
            attack_pattern_slug=selected_pattern.slug,
            strategy_summary=strategy_summary,
            adaptation_reason=adaptation_reason,
            turn_number=request.turn_number,
            model_id=generation.model_id,
            provider=generation.provider,
            latency_ms=generation.latency_ms,
            input_tokens=generation.input_tokens,
            output_tokens=generation.output_tokens,
            total_tokens=generation.total_tokens,
            metadata={
                "attacker_role": request.attacker_model.role,
                "third_party": request.attacker_model.third_party,
                "finish_reason": generation.finish_reason,
                "provider_metadata": RedAgentService._safe_metadata(
                    generation.raw_metadata
                ),
                "generation_attempts": generation_attempts,
                "objective_repair_used": objective_repair_used,
            },
        )

    @staticmethod
    def _safe_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
        reserved = {
            "access_token",
            "api_key",
            "authorization",
            "authorization_header",
            "hf_token",
            "password",
            "secret",
            "token",
        }

        def sanitize(item: Any) -> Any:
            if isinstance(item, Mapping):
                return {
                    str(key): sanitize(child)
                    for key, child in item.items()
                    if str(key).strip().lower().replace("-", "_") not in reserved
                }
            if isinstance(item, list):
                return [sanitize(child) for child in item]
            return item

        return sanitize(value)
