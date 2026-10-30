from typing import Annotated

from fastapi import Depends

from app.model_gateway.dependencies import get_model_gateway
from app.model_gateway.gateway import ModelGateway
from app.red_agent.service import RedAgentService


def get_red_agent_service(
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
) -> RedAgentService:
    return RedAgentService(gateway)
