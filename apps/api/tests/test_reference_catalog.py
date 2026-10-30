from datetime import date

from app.reference_data import (
    ATTACK_PATTERNS,
    OWASP_GENAI_LLM_TOP_10_2026,
    POLICY_PROFILES,
    SCENARIOS,
)


def scenario_risks(slug: str) -> tuple[str, ...]:
    return next(item for item in SCENARIOS if item.slug == slug).security_risk_codes


def test_owasp_2026_framework_and_risks_are_canonical() -> None:
    framework = OWASP_GENAI_LLM_TOP_10_2026
    codes = [risk.code for risk in framework.risks]

    assert framework.name == "OWASP GenAI LLM Top 10"
    assert framework.version == "2026"
    assert framework.release_date == date(2026, 8, 3)
    assert framework.source_url == (
        "https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/"
    )
    assert len(framework.risks) == 10
    assert len(codes) == len(set(codes))
    assert codes == [f"LLM{number:02}:2026" for number in range(1, 11)]


def test_scenario_and_attack_pattern_slugs_are_unique() -> None:
    scenario_slugs = [scenario.slug for scenario in SCENARIOS]
    attack_pattern_slugs = [pattern.slug for pattern in ATTACK_PATTERNS]

    assert len(scenario_slugs) == len(set(scenario_slugs)) == 9
    assert len(attack_pattern_slugs) == len(set(attack_pattern_slugs)) == 12


def test_security_scenarios_have_explicit_owasp_mappings() -> None:
    assert scenario_risks("jailbreak") == ("LLM01:2026",)
    assert scenario_risks("direct-prompt-injection") == ("LLM01:2026",)
    assert scenario_risks("indirect-prompt-injection") == ("LLM01:2026",)
    assert scenario_risks("sensitive-information-disclosure") == ("LLM02:2026",)
    assert scenario_risks("hidden-context-exposure") == ("LLM08:2026",)
    assert scenario_risks("misinformation") == ("LLM07:2026",)


def test_ai_safety_scenarios_have_no_forced_owasp_mapping() -> None:
    assert scenario_risks("toxicity") == ()
    assert scenario_risks("self-harm") == ()
    assert scenario_risks("model-policy-specification-violation") == ()


def test_initial_attack_pattern_mappings_are_project_configuration() -> None:
    patterns_by_scenario = {
        scenario.slug: scenario.attack_pattern_slugs for scenario in SCENARIOS
    }

    assert patterns_by_scenario["jailbreak"] == (
        "role_play_framing",
        "authority_impersonation",
        "hypothetical_framing",
        "instruction_override",
        "many_shot_priming",
        "multi_turn_escalation",
        "obfuscation",
        "encoded_payload",
        "multilingual_bypass",
    )
    assert patterns_by_scenario["direct-prompt-injection"] == (
        "instruction_override",
        "authority_impersonation",
        "obfuscation",
        "encoded_payload",
        "multilingual_bypass",
    )
    assert patterns_by_scenario["indirect-prompt-injection"] == (
        "indirect_injection",
        "obfuscation",
        "encoded_payload",
    )
    assert patterns_by_scenario["hidden-context-exposure"] == (
        "context_extraction",
        "authority_impersonation",
        "social_engineering_framing",
        "multi_turn_escalation",
    )


def test_policy_profiles_have_ordered_empty_future_configurations() -> None:
    assert [profile.slug for profile in POLICY_PROFILES] == [
        "strict",
        "moderate",
        "permissive",
    ]
    assert [profile.strictness_rank for profile in POLICY_PROFILES] == [3, 2, 1]
    assert all(
        profile.strictness_level == profile.slug for profile in POLICY_PROFILES
    )
