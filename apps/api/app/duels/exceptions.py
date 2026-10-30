from uuid import UUID


class DuelError(RuntimeError):
    """Base class for safe Duel application errors."""


class DuelNotFoundError(DuelError):
    def __init__(self, duel_id: UUID) -> None:
        super().__init__(f"Duel {duel_id} was not found")


class DuelLifecycleError(DuelError):
    pass


class DuelReferenceNotFoundError(DuelError):
    pass


class DuelExecutionFailedError(DuelError):
    def __init__(self, duel_id: UUID) -> None:
        self.duel_id = duel_id
        super().__init__("Duel execution failed")
