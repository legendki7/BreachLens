from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from app.domain.enums import DuelStatus, DuelTurnStatus
from app.schemas.common import DomainSchema, EntityRead


class DuelCreate(DomainSchema):
    scenario_id: UUID
    target_model_id: UUID
    policy_profile_id: UUID
    status: DuelStatus = DuelStatus.PENDING
    requested_turns: int = Field(gt=0)
    completed_turns: int = Field(default=0, ge=0)
    stop_on_first_breach: bool = True

    @model_validator(mode="after")
    def completed_turns_do_not_exceed_requested(self) -> "DuelCreate":
        if self.completed_turns > self.requested_turns:
            raise ValueError("completed_turns cannot exceed requested_turns")
        return self


class DuelRead(DuelCreate, EntityRead):
    started_at: datetime | None = None
    completed_at: datetime | None = None


class DuelTurnCreate(DomainSchema):
    duel_id: UUID
    turn_number: int = Field(gt=0)
    status: DuelTurnStatus = DuelTurnStatus.PENDING
    attack_pattern_id: UUID | None = None
    attack_prompt: str | None = None
    target_response: str | None = None


class DuelTurnRead(DuelTurnCreate, EntityRead):
    started_at: datetime | None = None
    completed_at: datetime | None = None

