"""SQLAlchemy domain models registered with the shared metadata."""

from app.models.duels import (
    Duel,
    DuelTurn,
    DuelTurnAttack,
    DuelTurnEvaluation,
    DuelTurnGuardrailReport,
    DuelTurnModelExecution,
)
from app.models.policies import PolicyProfile
from app.models.registry import ModelProvider, TargetModel
from app.models.scenarios import (
    AttackPattern,
    Scenario,
    ScenarioAttackPattern,
    ScenarioSecurityRisk,
)
from app.models.security import (
    SecurityFramework,
    SecurityFrameworkVersion,
    SecurityRisk,
)

__all__ = [
    "AttackPattern",
    "Duel",
    "DuelTurn",
    "DuelTurnAttack",
    "DuelTurnEvaluation",
    "DuelTurnGuardrailReport",
    "DuelTurnModelExecution",
    "ModelProvider",
    "PolicyProfile",
    "Scenario",
    "ScenarioAttackPattern",
    "ScenarioSecurityRisk",
    "SecurityFramework",
    "SecurityFrameworkVersion",
    "SecurityRisk",
    "TargetModel",
]
