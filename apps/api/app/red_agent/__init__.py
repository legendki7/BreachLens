"""Provider-independent adaptive attack generation."""

from app.red_agent.contracts import (
    AttackerModelConfiguration,
    PriorRedAgentTurn,
    RedAgentGenerationConfiguration,
    RedAgentRequest,
    RedAgentResult,
    RedAgentScenario,
    RedAgentAttackPattern,
)
from app.red_agent.service import RedAgentService

__all__ = [
    "AttackerModelConfiguration",
    "PriorRedAgentTurn",
    "RedAgentAttackPattern",
    "RedAgentGenerationConfiguration",
    "RedAgentRequest",
    "RedAgentResult",
    "RedAgentScenario",
    "RedAgentService",
]
