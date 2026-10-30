from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import DomainSchema, EntityRead, NonEmptyString


class ModelProviderCreate(DomainSchema):
    name: NonEmptyString
    slug: NonEmptyString
    provider_type: NonEmptyString
    base_url: str | None = None
    is_active: bool = True


class ModelProviderRead(ModelProviderCreate, EntityRead):
    pass


class TargetModelCreate(DomainSchema):
    provider_id: UUID
    display_name: NonEmptyString
    canonical_model_id: NonEmptyString
    description: str | None = None
    model_family: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    third_party: bool
    is_active: bool = True


class TargetModelRead(TargetModelCreate, EntityRead):
    pass

