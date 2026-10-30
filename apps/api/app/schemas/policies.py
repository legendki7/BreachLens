from typing import Any

from pydantic import Field

from app.schemas.common import DomainSchema, EntityRead, NonEmptyString


class PolicyProfileCreate(DomainSchema):
    name: NonEmptyString
    slug: NonEmptyString
    description: NonEmptyString
    strictness_level: NonEmptyString
    configuration: dict[str, Any] = Field(default_factory=dict)
    is_builtin: bool = False
    is_active: bool = True


class PolicyProfileRead(PolicyProfileCreate, EntityRead):
    pass

