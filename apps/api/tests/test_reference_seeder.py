import asyncio
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.reference_data.seeder import seed_reference_data
from app.reference_data.types import (
    AttackPatternDefinition,
    PolicyProfileDefinition,
    ScenarioDefinition,
    SecurityFrameworkDefinition,
    SecurityRiskDefinition,
)


@dataclass
class InMemoryReferenceDataRepository:
    frameworks: dict[str, tuple[UUID, SecurityFrameworkDefinition]] = field(
        default_factory=dict
    )
    framework_versions: dict[
        tuple[UUID, str], tuple[UUID, SecurityFrameworkDefinition]
    ] = field(default_factory=dict)
    risks: dict[
        tuple[UUID, str], tuple[UUID, SecurityRiskDefinition]
    ] = field(default_factory=dict)
    attack_patterns: dict[str, tuple[UUID, AttackPatternDefinition]] = field(
        default_factory=dict
    )
    scenarios: dict[str, tuple[UUID, ScenarioDefinition]] = field(
        default_factory=dict
    )
    policy_profiles: dict[str, tuple[UUID, PolicyProfileDefinition]] = field(
        default_factory=dict
    )
    scenario_risks: set[tuple[UUID, UUID]] = field(default_factory=set)
    scenario_attack_patterns: set[tuple[UUID, UUID]] = field(default_factory=set)

    async def upsert_framework(
        self,
        definition: SecurityFrameworkDefinition,
    ) -> UUID:
        record_id = self.frameworks.get(definition.slug, (uuid4(), definition))[0]
        self.frameworks[definition.slug] = (record_id, definition)
        return record_id

    async def upsert_framework_version(
        self,
        framework_id: UUID,
        definition: SecurityFrameworkDefinition,
    ) -> UUID:
        key = (framework_id, definition.version)
        record_id = self.framework_versions.get(key, (uuid4(), definition))[0]
        self.framework_versions[key] = (record_id, definition)
        return record_id

    async def upsert_security_risk(
        self,
        framework_version_id: UUID,
        definition: SecurityRiskDefinition,
    ) -> UUID:
        key = (framework_version_id, definition.code)
        record_id = self.risks.get(key, (uuid4(), definition))[0]
        self.risks[key] = (record_id, definition)
        return record_id

    async def upsert_attack_pattern(
        self,
        definition: AttackPatternDefinition,
    ) -> UUID:
        record_id = self.attack_patterns.get(definition.slug, (uuid4(), definition))[0]
        self.attack_patterns[definition.slug] = (record_id, definition)
        return record_id

    async def upsert_scenario(self, definition: ScenarioDefinition) -> UUID:
        record_id = self.scenarios.get(definition.slug, (uuid4(), definition))[0]
        self.scenarios[definition.slug] = (record_id, definition)
        return record_id

    async def upsert_policy_profile(
        self,
        definition: PolicyProfileDefinition,
    ) -> UUID:
        record_id = self.policy_profiles.get(definition.slug, (uuid4(), definition))[0]
        self.policy_profiles[definition.slug] = (record_id, definition)
        return record_id

    async def ensure_scenario_risk(
        self,
        scenario_id: UUID,
        risk_id: UUID,
    ) -> None:
        self.scenario_risks.add((scenario_id, risk_id))

    async def ensure_scenario_attack_pattern(
        self,
        scenario_id: UUID,
        attack_pattern_id: UUID,
    ) -> None:
        self.scenario_attack_patterns.add((scenario_id, attack_pattern_id))

    async def flush(self) -> None:
        return None


def test_reference_data_seeding_is_idempotent() -> None:
    repository = InMemoryReferenceDataRepository()

    first_summary = asyncio.run(seed_reference_data(repository))
    ids_after_first_run = {
        "frameworks": {record[0] for record in repository.frameworks.values()},
        "versions": {record[0] for record in repository.framework_versions.values()},
        "risks": {record[0] for record in repository.risks.values()},
        "patterns": {record[0] for record in repository.attack_patterns.values()},
        "scenarios": {record[0] for record in repository.scenarios.values()},
        "profiles": {record[0] for record in repository.policy_profiles.values()},
    }
    second_summary = asyncio.run(seed_reference_data(repository))

    assert second_summary == first_summary
    assert first_summary.frameworks == 1
    assert first_summary.framework_versions == 1
    assert first_summary.security_risks == len(repository.risks) == 10
    assert first_summary.attack_patterns == len(repository.attack_patterns) == 12
    assert first_summary.scenarios == len(repository.scenarios) == 9
    assert first_summary.policy_profiles == len(repository.policy_profiles) == 3
    assert first_summary.scenario_risk_mappings == len(repository.scenario_risks) == 6
    assert (
        first_summary.scenario_attack_pattern_mappings
        == len(repository.scenario_attack_patterns)
        == 21
    )
    assert ids_after_first_run == {
        "frameworks": {record[0] for record in repository.frameworks.values()},
        "versions": {record[0] for record in repository.framework_versions.values()},
        "risks": {record[0] for record in repository.risks.values()},
        "patterns": {record[0] for record in repository.attack_patterns.values()},
        "scenarios": {record[0] for record in repository.scenarios.values()},
        "profiles": {record[0] for record in repository.policy_profiles.values()},
    }
