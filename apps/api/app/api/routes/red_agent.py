import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.model_gateway.exceptions import (
    ModelTimeoutError,
    ProviderNotConfiguredError,
    ProviderNotSupportedError,
)
from app.red_agent.contracts import (
    RedAgentAttackPattern,
    RedAgentRequest,
    RedAgentResult,
    RedAgentScenario,
)
from app.red_agent.dependencies import get_red_agent_service
from app.red_agent.exceptions import (
    InvalidAttackPatternError,
    RedAgentGenerationError,
    RedAgentOutputValidationError,
    ScenarioAttackPatternsUnavailableError,
)
from app.red_agent.service import RedAgentService
from app.reference_data import ATTACK_PATTERNS, SCENARIOS
from app.schemas.red_agent import RedAgentGenerateRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/generate",
    response_model=RedAgentResult,
    summary="Generate one development Red Agent attack",
)
async def generate_attack(
    payload: RedAgentGenerateRequest,
    service: Annotated[RedAgentService, Depends(get_red_agent_service)],
) -> RedAgentResult:
    scenario_definition = next(
        (scenario for scenario in SCENARIOS if scenario.slug == payload.scenario_slug),
        None,
    )
    if scenario_definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    patterns_by_slug = {pattern.slug: pattern for pattern in ATTACK_PATTERNS}
    allowed_patterns = tuple(
        RedAgentAttackPattern(
            name=patterns_by_slug[slug].name,
            slug=slug,
            description=patterns_by_slug[slug].description,
            category=patterns_by_slug[slug].category,
        )
        for slug in scenario_definition.attack_pattern_slugs
    )
    request = RedAgentRequest(
        scenario=RedAgentScenario(
            name=scenario_definition.name,
            slug=scenario_definition.slug,
            description=scenario_definition.description,
            severity=scenario_definition.severity,
        ),
        allowed_attack_patterns=allowed_patterns,
        attack_pattern_slug=payload.attack_pattern_slug,
        target_system_prompt=payload.target_system_prompt,
        turn_number=payload.turn_number,
        max_turns=payload.max_turns,
        prior_turns=payload.prior_turns,
        objective=payload.objective,
        contextual_metadata=payload.contextual_metadata,
        attacker_model=payload.attacker_model,
        generation=payload.generation,
    )

    try:
        return await service.generate(request)
    except InvalidAttackPatternError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Attack pattern is not allowed for the selected scenario",
        ) from None
    except ScenarioAttackPatternsUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected scenario has no configured attack patterns",
        ) from None
    except RedAgentOutputValidationError:
        logger.warning(
            "Attacker model returned invalid output for scenario %s",
            scenario_definition.slug,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Attacker model returned invalid structured output",
        ) from None
    except RedAgentGenerationError as exc:
        cause = exc.__cause__
        if isinstance(cause, ProviderNotSupportedError):
            response_status = status.HTTP_422_UNPROCESSABLE_CONTENT
            detail = "Attacker model provider is not supported"
        elif isinstance(cause, ProviderNotConfiguredError):
            response_status = status.HTTP_503_SERVICE_UNAVAILABLE
            detail = "Attacker model provider is not configured"
        elif isinstance(cause, ModelTimeoutError):
            response_status = status.HTTP_504_GATEWAY_TIMEOUT
            detail = "Attacker model request timed out"
        else:
            response_status = status.HTTP_502_BAD_GATEWAY
            detail = "Attacker model generation failed"
        logger.warning(
            "Red Agent generation failed for scenario %s using provider %s",
            scenario_definition.slug,
            exc.provider,
        )
        raise HTTPException(status_code=response_status, detail=detail) from None
