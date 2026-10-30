from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.duels.orchestrator import DuelOrchestrator
from app.duels.repository import DuelRepository, SqlAlchemyDuelRepository
from app.evaluation.dependencies import get_evaluation_service
from app.evaluation.service import EvaluationService
from app.guardrails.dependencies import get_guardrail_engine
from app.guardrails.engine import GuardrailEngine
from app.model_gateway.dependencies import get_model_gateway
from app.model_gateway.gateway import ModelGateway
from app.red_agent.dependencies import get_red_agent_service
from app.red_agent.service import RedAgentService


def get_duel_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DuelRepository:
    return SqlAlchemyDuelRepository(session)


def get_duel_orchestrator(
    red_agent: Annotated[RedAgentService, Depends(get_red_agent_service)],
    guardrails: Annotated[GuardrailEngine, Depends(get_guardrail_engine)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
    evaluation: Annotated[EvaluationService, Depends(get_evaluation_service)],
    repository: Annotated[DuelRepository, Depends(get_duel_repository)],
) -> DuelOrchestrator:
    return DuelOrchestrator(
        red_agent,
        guardrails,
        gateway,
        evaluation,
        repository,
    )
