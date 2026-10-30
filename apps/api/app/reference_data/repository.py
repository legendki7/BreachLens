from __future__ import annotations

from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policies import PolicyProfile
from app.models.scenarios import (
    AttackPattern,
    Scenario,
    ScenarioAttackPattern,
    ScenarioSecurityRisk,
)
from app.models.security import (
    SecurityFramework,
    SecurityFrameworkVersion,
    SecurityRisk,
)
from app.reference_data.types import (
    AttackPatternDefinition,
    PolicyProfileDefinition,
    ScenarioDefinition,
    SecurityFrameworkDefinition,
    SecurityRiskDefinition,
)


class ReferenceDataRepository(Protocol):
    async def upsert_framework(self, definition: SecurityFrameworkDefinition) -> UUID: ...

    async def upsert_framework_version(
        self,
        framework_id: UUID,
        definition: SecurityFrameworkDefinition,
    ) -> UUID: ...

    async def upsert_security_risk(
        self,
        framework_version_id: UUID,
        definition: SecurityRiskDefinition,
    ) -> UUID: ...

    async def upsert_attack_pattern(self, definition: AttackPatternDefinition) -> UUID: ...

    async def upsert_scenario(self, definition: ScenarioDefinition) -> UUID: ...

    async def upsert_policy_profile(self, definition: PolicyProfileDefinition) -> UUID: ...

    async def ensure_scenario_risk(self, scenario_id: UUID, risk_id: UUID) -> None: ...

    async def ensure_scenario_attack_pattern(
        self,
        scenario_id: UUID,
        attack_pattern_id: UUID,
    ) -> None: ...

    async def flush(self) -> None: ...


class SqlAlchemyReferenceDataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_framework(self, definition: SecurityFrameworkDefinition) -> UUID:
        record = await self._session.scalar(
            select(SecurityFramework).where(SecurityFramework.slug == definition.slug)
        )
        if record is None:
            record = SecurityFramework(id=uuid4(), slug=definition.slug)
            self._session.add(record)

        record.name = definition.name
        record.description = definition.description
        return record.id

    async def upsert_framework_version(
        self,
        framework_id: UUID,
        definition: SecurityFrameworkDefinition,
    ) -> UUID:
        record = await self._session.scalar(
            select(SecurityFrameworkVersion).where(
                SecurityFrameworkVersion.framework_id == framework_id,
                SecurityFrameworkVersion.version == definition.version,
            )
        )
        if record is None:
            record = SecurityFrameworkVersion(
                id=uuid4(),
                framework_id=framework_id,
                version=definition.version,
            )
            self._session.add(record)

        record.release_date = definition.release_date
        record.source_url = definition.source_url
        record.is_active = True
        return record.id

    async def upsert_security_risk(
        self,
        framework_version_id: UUID,
        definition: SecurityRiskDefinition,
    ) -> UUID:
        record = await self._session.scalar(
            select(SecurityRisk).where(
                SecurityRisk.framework_version_id == framework_version_id,
                SecurityRisk.code == definition.code,
            )
        )
        if record is None:
            record = SecurityRisk(
                id=uuid4(),
                framework_version_id=framework_version_id,
                code=definition.code,
            )
            self._session.add(record)

        record.name = definition.name
        record.description = definition.description
        record.severity = None
        record.sort_order = definition.sort_order
        return record.id

    async def upsert_attack_pattern(self, definition: AttackPatternDefinition) -> UUID:
        record = await self._session.scalar(
            select(AttackPattern).where(AttackPattern.slug == definition.slug)
        )
        if record is None:
            record = AttackPattern(id=uuid4(), slug=definition.slug)
            self._session.add(record)

        record.name = definition.name
        record.description = definition.description
        record.category = definition.category
        return record.id

    async def upsert_scenario(self, definition: ScenarioDefinition) -> UUID:
        record = await self._session.scalar(
            select(Scenario).where(Scenario.slug == definition.slug)
        )
        if record is None:
            record = Scenario(id=uuid4(), slug=definition.slug)
            self._session.add(record)

        record.name = definition.name
        record.description = definition.description
        record.severity = definition.severity
        record.target_system_prompt = definition.target_system_prompt
        record.is_builtin = True
        record.is_active = True
        return record.id

    async def upsert_policy_profile(self, definition: PolicyProfileDefinition) -> UUID:
        record = await self._session.scalar(
            select(PolicyProfile).where(PolicyProfile.slug == definition.slug)
        )
        if record is None:
            record = PolicyProfile(
                id=uuid4(),
                slug=definition.slug,
                configuration={},
            )
            self._session.add(record)

        record.name = definition.name
        record.description = definition.description
        record.strictness_level = definition.strictness_level
        record.is_builtin = True
        record.is_active = True
        return record.id

    async def ensure_scenario_risk(self, scenario_id: UUID, risk_id: UUID) -> None:
        record = await self._session.scalar(
            select(ScenarioSecurityRisk).where(
                ScenarioSecurityRisk.scenario_id == scenario_id,
                ScenarioSecurityRisk.security_risk_id == risk_id,
            )
        )
        if record is None:
            self._session.add(
                ScenarioSecurityRisk(
                    scenario_id=scenario_id,
                    security_risk_id=risk_id,
                )
            )

    async def ensure_scenario_attack_pattern(
        self,
        scenario_id: UUID,
        attack_pattern_id: UUID,
    ) -> None:
        record = await self._session.scalar(
            select(ScenarioAttackPattern).where(
                ScenarioAttackPattern.scenario_id == scenario_id,
                ScenarioAttackPattern.attack_pattern_id == attack_pattern_id,
            )
        )
        if record is None:
            self._session.add(
                ScenarioAttackPattern(
                    scenario_id=scenario_id,
                    attack_pattern_id=attack_pattern_id,
                )
            )

    async def flush(self) -> None:
        await self._session.flush()
