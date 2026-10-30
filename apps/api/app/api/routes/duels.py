from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.duels.contracts import (
    CreateDuelRequest,
    DuelCreated,
    DuelExecutionResult,
    StartDuelRequest,
)
from app.duels.dependencies import get_duel_orchestrator, get_duel_repository
from app.duels.exceptions import (
    DuelLifecycleError,
    DuelNotFoundError,
    DuelReferenceNotFoundError,
)
from app.duels.orchestrator import DuelOrchestrator
from app.duels.repository import DuelRepository

router = APIRouter()


@router.post(
    "",
    response_model=DuelCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pending Duel",
)
async def create_duel(
    payload: CreateDuelRequest,
    repository: Annotated[DuelRepository, Depends(get_duel_repository)],
) -> DuelCreated:
    try:
        return await repository.create(payload)
    except DuelReferenceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from None


@router.post(
    "/{duel_id}/run",
    response_model=DuelExecutionResult,
    summary="Run one pending Duel to a terminal state",
)
async def run_duel(
    duel_id: UUID,
    payload: StartDuelRequest,
    orchestrator: Annotated[DuelOrchestrator, Depends(get_duel_orchestrator)],
) -> DuelExecutionResult:
    try:
        return await orchestrator.run(duel_id, payload)
    except DuelNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Duel not found",
        ) from None
    except DuelLifecycleError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from None


@router.get(
    "/{duel_id}",
    response_model=DuelExecutionResult,
    summary="Get persisted Duel evidence",
)
async def get_duel(
    duel_id: UUID,
    repository: Annotated[DuelRepository, Depends(get_duel_repository)],
) -> DuelExecutionResult:
    try:
        return await repository.get_result(duel_id)
    except DuelNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Duel not found",
        ) from None
