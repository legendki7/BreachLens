from app.domain.enums import DuelStatus, DuelTurnStatus
from app.duels.exceptions import DuelLifecycleError

DUEL_TRANSITIONS: dict[DuelStatus, frozenset[DuelStatus]] = {
    DuelStatus.PENDING: frozenset({DuelStatus.RUNNING}),
    DuelStatus.RUNNING: frozenset(
        {DuelStatus.COMPLETED, DuelStatus.STOPPED, DuelStatus.FAILED}
    ),
    DuelStatus.COMPLETED: frozenset(),
    DuelStatus.STOPPED: frozenset(),
    DuelStatus.FAILED: frozenset(),
}

TURN_TRANSITIONS: dict[DuelTurnStatus, frozenset[DuelTurnStatus]] = {
    DuelTurnStatus.PENDING: frozenset(
        {DuelTurnStatus.GENERATING_ATTACK, DuelTurnStatus.FAILED}
    ),
    DuelTurnStatus.GENERATING_ATTACK: frozenset(
        {DuelTurnStatus.SCANNING_INPUT, DuelTurnStatus.FAILED}
    ),
    DuelTurnStatus.SCANNING_INPUT: frozenset(
        {
            DuelTurnStatus.AWAITING_MODEL,
            DuelTurnStatus.EVALUATING,
            DuelTurnStatus.FAILED,
        }
    ),
    DuelTurnStatus.AWAITING_MODEL: frozenset(
        {DuelTurnStatus.SCANNING_OUTPUT, DuelTurnStatus.FAILED}
    ),
    DuelTurnStatus.SCANNING_OUTPUT: frozenset(
        {DuelTurnStatus.EVALUATING, DuelTurnStatus.FAILED}
    ),
    DuelTurnStatus.EVALUATING: frozenset(
        {DuelTurnStatus.COMPLETED, DuelTurnStatus.FAILED}
    ),
    DuelTurnStatus.COMPLETED: frozenset(),
    DuelTurnStatus.FAILED: frozenset(),
}


def validate_duel_transition(current: DuelStatus, target: DuelStatus) -> None:
    if target not in DUEL_TRANSITIONS[current]:
        raise DuelLifecycleError(
            f"Duel cannot transition from {current.value} to {target.value}"
        )


def validate_turn_transition(current: DuelTurnStatus, target: DuelTurnStatus) -> None:
    if target not in TURN_TRANSITIONS[current]:
        raise DuelLifecycleError(
            f"Duel turn cannot transition from {current.value} to {target.value}"
        )
