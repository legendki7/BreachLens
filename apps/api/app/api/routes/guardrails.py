import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.guardrails.contracts import (
    GuardrailExecutionReport,
    GuardrailPolicyContext,
    GuardrailRequest,
    GuardrailScenarioContext,
)
from app.guardrails.dependencies import get_guardrail_engine
from app.guardrails.engine import GuardrailEngine
from app.guardrails.exceptions import (
    GuardrailAdapterUnavailableError,
    GuardrailConfigurationError,
    GuardrailExecutionError,
    UnsupportedGuardrailStageError,
)
from app.reference_data import POLICY_PROFILES, SCENARIOS
from app.schemas.guardrails import GuardrailTestRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/test",
    response_model=GuardrailExecutionReport,
    summary="Test one isolated guardrail stage",
)
async def test_guardrails(
    payload: GuardrailTestRequest,
    engine: Annotated[GuardrailEngine, Depends(get_guardrail_engine)],
) -> GuardrailExecutionReport:
    scenario = next(
        (item for item in SCENARIOS if item.slug == payload.scenario_slug),
        None,
    )
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )
    profile = next(
        (item for item in POLICY_PROFILES if item.slug == payload.policy_profile_slug),
        None,
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy profile not found",
        )

    nemo_enabled = payload.adapters is not None and "nemo" in payload.adapters
    request = GuardrailRequest(
        stage=payload.stage,
        content=payload.content,
        scenario=GuardrailScenarioContext(
            name=scenario.name,
            slug=scenario.slug,
            description=scenario.description,
        ),
        policy_profile=GuardrailPolicyContext(
            name=profile.name,
            slug=profile.slug,
            strictness_level=profile.strictness_level,
            configuration={"nemo_enabled": nemo_enabled},
        ),
        target_model=payload.target_model,
        turn_number=payload.turn_number,
        metadata=payload.metadata,
    )
    try:
        return await engine.execute(request, payload.adapters)
    except GuardrailAdapterUnavailableError as exc:
        logger.warning("Requested guardrail adapter unavailable: %s", exc.adapter)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Requested guardrail adapter is unavailable",
        ) from None
    except GuardrailConfigurationError:
        logger.warning("Guardrail policy or adapter configuration is invalid")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Guardrail configuration is invalid",
        ) from None
    except UnsupportedGuardrailStageError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Guardrail stage is unsupported",
        ) from None
    except GuardrailExecutionError:
        logger.exception("Guardrail engine execution failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Guardrail execution failed",
        ) from None
