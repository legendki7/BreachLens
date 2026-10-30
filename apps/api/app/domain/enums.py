from enum import StrEnum


class ScenarioSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DuelStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class DuelTurnStatus(StrEnum):
    PENDING = "pending"
    GENERATING_ATTACK = "generating_attack"
    SCANNING_INPUT = "scanning_input"
    AWAITING_MODEL = "awaiting_model"
    SCANNING_OUTPUT = "scanning_output"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    """Return persisted string values for a SQLAlchemy Enum."""

    return [member.value for member in enum_class]

