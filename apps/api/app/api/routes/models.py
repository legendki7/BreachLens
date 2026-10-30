import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.model_gateway.contracts import (
    ModelGenerationRequest,
    ModelGenerationResult,
    ModelMessage,
    ModelRole,
)
from app.model_gateway.dependencies import get_model_gateway
from app.model_gateway.exceptions import (
    ModelExecutionError,
    ModelTimeoutError,
    ProviderNotConfiguredError,
    ProviderNotSupportedError,
)
from app.model_gateway.gateway import ModelGateway
from app.models.registry import TargetModel
from app.schemas.model_test import ModelTestRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/test", response_model=ModelGenerationResult)
async def test_model(
    payload: ModelTestRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
) -> ModelGenerationResult:
    query = (
        select(TargetModel)
        .options(selectinload(TargetModel.provider))
        .where(TargetModel.id == payload.target_model_id)
    )
    target_model = (await session.execute(query)).scalar_one_or_none()

    if target_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target model not found",
        )
    if not target_model.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Target model is inactive",
        )

    messages: list[ModelMessage] = []
    if payload.system_message is not None:
        messages.append(
            ModelMessage(role=ModelRole.SYSTEM, content=payload.system_message)
        )
    messages.append(ModelMessage(role=ModelRole.USER, content=payload.user_message))

    try:
        return await gateway.generate(
            target_model,
            ModelGenerationRequest(messages=messages),
        )
    except ProviderNotSupportedError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Target model provider is not supported",
        ) from None
    except ProviderNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Target model provider is not configured",
        ) from None
    except ModelTimeoutError:
        logger.warning("Model test timed out for target model %s", target_model.id)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Model request timed out",
        ) from None
    except ModelExecutionError:
        logger.exception("Model test failed for target model %s", target_model.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model execution failed",
        ) from None

