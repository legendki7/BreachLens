from dataclasses import dataclass
from datetime import date

from app.domain.enums import ScenarioSeverity


@dataclass(frozen=True, slots=True)
class SecurityRiskDefinition:
    code: str
    name: str
    description: str
    sort_order: int


@dataclass(frozen=True, slots=True)
class SecurityFrameworkDefinition:
    name: str
    slug: str
    description: str
    version: str
    release_date: date
    source_url: str
    risks: tuple[SecurityRiskDefinition, ...]


@dataclass(frozen=True, slots=True)
class AttackPatternDefinition:
    name: str
    slug: str
    description: str
    category: str | None = None


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    name: str
    slug: str
    description: str
    severity: ScenarioSeverity
    target_system_prompt: str
    security_risk_codes: tuple[str, ...] = ()
    attack_pattern_slugs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PolicyProfileDefinition:
    name: str
    slug: str
    description: str
    strictness_level: str
    strictness_rank: int

