import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.evaluation.contracts import (
    BlueEvaluationRequest,
    EvaluationAttackPattern,
    EvaluationScenario,
    SecurityEvaluationResult,
)
from app.evaluation.dependencies import get_evaluation_service
from app.evaluation.exceptions import (
    JudgeGenerationError,
    JudgeOutputValidationError,
    RubricConfigurationError,
    RubricNotFoundError,
)
from app.evaluation.service import EvaluationService
from app.model_gateway.exceptions import (
    ModelTimeoutError,
    ProviderNotConfiguredError,
    ProviderNotSupportedError,
)
from app.reference_data import ATTACK_PATTERNS, SCENARIOS
from app.schemas.evaluation import EvaluationTestRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/test",
    response_model=SecurityEvaluationResult,
    summary="Evaluate one already-produced interaction",
)
async def test_evaluation(
    payload: EvaluationTestRequest,
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> SecurityEvaluationResult:
    scenario = next(
        (item for item in SCENARIOS if item.slug == payload.scenario_slug),
        None,
    )
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )
    attack_pattern = next(
        (item for item in ATTACK_PATTERNS if item.slug == payload.attack_pattern_slug),
        None,
    )
    if attack_pattern is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attack pattern not found",
        )

    request = BlueEvaluationRequest(
        scenario=EvaluationScenario(
            name=scenario.name,
            slug=scenario.slug,
            description=scenario.description,
        ),
        attack_pattern=EvaluationAttackPattern(
            name=attack_pattern.name,
            slug=attack_pattern.slug,
            description=attack_pattern.description,
        ),
        attack_prompt=payload.attack_prompt,
        target_response=payload.target_response,
        target_was_called=payload.target_was_called,
        target_system_prompt=payload.target_system_prompt,
        input_guardrail_report=payload.input_guardrail_report,
        output_guardrail_report=payload.output_guardrail_report,
        turn_number=payload.turn_number,
        prior_turns=payload.prior_turns,
        trusted_context=payload.trusted_context,
        evaluation_context=payload.evaluation_context,
    )
    try:
        return await service.evaluate(request, payload.judge_model)
    except RubricNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario rubric not found",
        ) from None
    except RubricConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Evaluation configuration is incomplete",
        ) from None
    except JudgeOutputValidationError:
        logger.warning("Judge model returned invalid structured output")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Judge model returned invalid structured output",
        ) from None
    except JudgeGenerationError as exc:
        cause = exc.__cause__
        if isinstance(cause, ProviderNotSupportedError):
            response_status = status.HTTP_422_UNPROCESSABLE_CONTENT
            detail = "Judge model provider is not supported"
        elif isinstance(cause, ProviderNotConfiguredError):
            response_status = status.HTTP_503_SERVICE_UNAVAILABLE
            detail = "Judge model provider is not configured"
        elif isinstance(cause, ModelTimeoutError):
            response_status = status.HTTP_504_GATEWAY_TIMEOUT
            detail = "Judge model request timed out"
        else:
            response_status = status.HTTP_502_BAD_GATEWAY
            detail = "Judge model generation failed"
        logger.warning("Judge generation failed using provider %s", exc.provider)
        raise HTTPException(status_code=response_status, detail=detail) from None
