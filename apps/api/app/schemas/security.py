from datetime import date
from uuid import UUID

from pydantic import Field

from app.schemas.common import DomainSchema, EntityRead, NonEmptyString


class SecurityFrameworkCreate(DomainSchema):
    name: NonEmptyString
    slug: NonEmptyString
    description: NonEmptyString


class SecurityFrameworkRead(SecurityFrameworkCreate, EntityRead):
    pass


class SecurityFrameworkVersionCreate(DomainSchema):
    framework_id: UUID
    version: NonEmptyString
    release_date: date | None = None
    source_url: str | None = None
    is_active: bool = True


class SecurityFrameworkVersionRead(SecurityFrameworkVersionCreate, EntityRead):
    pass


class SecurityRiskCreate(DomainSchema):
    framework_version_id: UUID
    code: NonEmptyString
    name: NonEmptyString
    description: NonEmptyString
    severity: str | None = None
    sort_order: int = Field(default=0, ge=0)


class SecurityRiskRead(SecurityRiskCreate, EntityRead):
    pass

