from __future__ import annotations

from dataclasses import dataclass

from app.reference_data.catalog import (
    ATTACK_PATTERNS,
    OWASP_GENAI_LLM_TOP_10_2026,
    POLICY_PROFILES,
    SCENARIOS,
)
from app.reference_data.repository import ReferenceDataRepository
from app.reference_data.types import (
    AttackPatternDefinition,
    PolicyProfileDefinition,
    ScenarioDefinition,
    SecurityFrameworkDefinition,
)


@dataclass(frozen=True, slots=True)
class SeedSummary:
    frameworks: int
    framework_versions: int
    security_risks: int
    attack_patterns: int
    scenarios: int
    policy_profiles: int
    scenario_risk_mappings: int
    scenario_attack_pattern_mappings: int


async def seed_reference_data(
    repository: ReferenceDataRepository,
    framework: SecurityFrameworkDefinition = OWASP_GENAI_LLM_TOP_10_2026,
    attack_patterns: tuple[AttackPatternDefinition, ...] = ATTACK_PATTERNS,
    scenarios: tuple[ScenarioDefinition, ...] = SCENARIOS,
    policy_profiles: tuple[PolicyProfileDefinition, ...] = POLICY_PROFILES,
) -> SeedSummary:
    framework_id = await repository.upsert_framework(framework)
    framework_version_id = await repository.upsert_framework_version(
        framework_id,
        framework,
    )

    risk_ids = {
        risk.code: await repository.upsert_security_risk(framework_version_id, risk)
        for risk in framework.risks
    }
    attack_pattern_ids = {
        pattern.slug: await repository.upsert_attack_pattern(pattern)
        for pattern in attack_patterns
    }
    scenario_ids = {
        scenario.slug: await repository.upsert_scenario(scenario)
        for scenario in scenarios
    }
    for profile in policy_profiles:
        await repository.upsert_policy_profile(profile)

    await repository.flush()

    scenario_risk_mapping_count = 0
    scenario_attack_pattern_mapping_count = 0
    for scenario in scenarios:
        scenario_id = scenario_ids[scenario.slug]
        for risk_code in scenario.security_risk_codes:
            try:
                risk_id = risk_ids[risk_code]
            except KeyError as error:
                raise ValueError(
                    f"Scenario {scenario.slug!r} references unknown risk {risk_code!r}"
                ) from error
            await repository.ensure_scenario_risk(scenario_id, risk_id)
            scenario_risk_mapping_count += 1

        for attack_pattern_slug in scenario.attack_pattern_slugs:
            try:
                attack_pattern_id = attack_pattern_ids[attack_pattern_slug]
            except KeyError as error:
                raise ValueError(
                    f"Scenario {scenario.slug!r} references unknown attack pattern "
                    f"{attack_pattern_slug!r}"
                ) from error
            await repository.ensure_scenario_attack_pattern(
                scenario_id,
                attack_pattern_id,
            )
            scenario_attack_pattern_mapping_count += 1

    await repository.flush()

    return SeedSummary(
        frameworks=1,
        framework_versions=1,
        security_risks=len(framework.risks),
        attack_patterns=len(attack_patterns),
        scenarios=len(scenarios),
        policy_profiles=len(policy_profiles),
        scenario_risk_mappings=scenario_risk_mapping_count,
        scenario_attack_pattern_mappings=scenario_attack_pattern_mapping_count,
    )
