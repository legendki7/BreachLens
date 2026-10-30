from app.domain.enums import ScenarioSeverity
from app.schemas.common import DomainSchema, EntityRead, NonEmptyString


class AttackPatternCreate(DomainSchema):
    name: NonEmptyString
    slug: NonEmptyString
    description: NonEmptyString
    category: str | None = None


class AttackPatternRead(AttackPatternCreate, EntityRead):
    pass


class ScenarioCreate(DomainSchema):
    name: NonEmptyString
    slug: NonEmptyString
    description: NonEmptyString
    severity: ScenarioSeverity
    target_system_prompt: NonEmptyString
    is_builtin: bool = False
    is_active: bool = True


class ScenarioRead(ScenarioCreate, EntityRead):
    pass

