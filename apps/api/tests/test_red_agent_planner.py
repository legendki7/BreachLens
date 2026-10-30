from app.domain.enums import ScenarioSeverity
from app.red_agent.contracts import (
    PriorRedAgentTurn,
    PriorTurnOutcome,
    RedAgentAttackPattern,
    RedAgentScenario,
)
from app.red_agent.planner import AttackStrategyPlanner


def scenario() -> RedAgentScenario:
    return RedAgentScenario(
        name="Jailbreak",
        slug="jailbreak",
        description="Test whether intended behavior can be bypassed.",
        severity=ScenarioSeverity.CRITICAL,
    )


def pattern(slug: str) -> RedAgentAttackPattern:
    return RedAgentAttackPattern(
        name=slug.replace("_", " ").title(),
        slug=slug,
        description=f"Apply {slug}.",
    )


def prior_turn(
    number: int,
    pattern_slug: str,
    outcome: PriorTurnOutcome | None = None,
    feedback: str | None = None,
) -> PriorRedAgentTurn:
    return PriorRedAgentTurn(
        turn_number=number,
        attack_pattern_slug=pattern_slug,
        attack_prompt="Previous attack",
        target_response="Previous response",
        outcome=outcome,
        evaluator_feedback=feedback,
    )


def test_planner_selects_first_configured_pattern_deterministically() -> None:
    patterns = (pattern("role_play_framing"), pattern("authority_impersonation"))
    planner = AttackStrategyPlanner()

    first = planner.select_pattern(scenario(), patterns, (), 1)
    repeated = planner.select_pattern(scenario(), patterns, (), 1)

    assert first.slug == repeated.slug == "role_play_framing"


def test_planner_avoids_immediate_pattern_repetition() -> None:
    patterns = (pattern("role_play_framing"), pattern("authority_impersonation"))
    turns = (
        prior_turn(1, "role_play_framing", PriorTurnOutcome.SAFE_REFUSAL),
    )

    selected = AttackStrategyPlanner().select_pattern(scenario(), patterns, turns, 2)

    assert selected.slug == "authority_impersonation"


def test_planner_prioritizes_an_untried_technique() -> None:
    patterns = (
        pattern("role_play_framing"),
        pattern("authority_impersonation"),
        pattern("obfuscation"),
    )
    turns = (
        prior_turn(1, "role_play_framing"),
        prior_turn(2, "authority_impersonation"),
    )

    selected = AttackStrategyPlanner().select_pattern(scenario(), patterns, turns, 3)

    assert selected.slug == "obfuscation"


def test_planner_reuses_the_most_effective_pattern_after_all_are_tried() -> None:
    patterns = (pattern("role_play_framing"), pattern("authority_impersonation"))
    turns = (
        prior_turn(1, "role_play_framing", PriorTurnOutcome.SAFE_REFUSAL),
        prior_turn(2, "authority_impersonation", PriorTurnOutcome.COMPLIANCE),
    )

    selected = AttackStrategyPlanner().select_pattern(scenario(), patterns, turns, 3)

    assert selected.slug == "authority_impersonation"


def test_planner_prefers_multi_turn_escalation_after_partial_compliance() -> None:
    patterns = (
        pattern("role_play_framing"),
        pattern("authority_impersonation"),
        pattern("multi_turn_escalation"),
    )
    turns = (
        prior_turn(
            1,
            "role_play_framing",
            feedback="The target showed partial compliance with the request.",
        ),
    )

    selected = AttackStrategyPlanner().select_pattern(scenario(), patterns, turns, 2)

    assert selected.slug == "multi_turn_escalation"
