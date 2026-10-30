from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DomainSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class EntityRead(DomainSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

