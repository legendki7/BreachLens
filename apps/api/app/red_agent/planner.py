from app.red_agent.contracts import (
    PriorRedAgentTurn,
    PriorTurnOutcome,
    RedAgentAttackPattern,
    RedAgentScenario,
)
from app.red_agent.exceptions import ScenarioAttackPatternsUnavailableError

MULTI_TURN_ESCALATION_SLUG = "multi_turn_escalation"


class AttackStrategyPlanner:
    """Select the next configured technique using reproducible evidence."""

    def select_pattern(
        self,
        scenario: RedAgentScenario,
        allowed_patterns: tuple[RedAgentAttackPattern, ...],
        prior_turns: tuple[PriorRedAgentTurn, ...],
        turn_number: int,
    ) -> RedAgentAttackPattern:
        if not allowed_patterns:
            raise ScenarioAttackPatternsUnavailableError(scenario.slug)
        if turn_number <= 0:
            raise ValueError("turn_number must be positive")

        if not prior_turns:
            return allowed_patterns[0]

        patterns_by_slug = {pattern.slug: pattern for pattern in allowed_patterns}
        last_turn = max(prior_turns, key=lambda turn: turn.turn_number)
        if (
            self._indicates_partial_compliance(last_turn)
            and MULTI_TURN_ESCALATION_SLUG in patterns_by_slug
            and last_turn.attack_pattern_slug != MULTI_TURN_ESCALATION_SLUG
        ):
            return patterns_by_slug[MULTI_TURN_ESCALATION_SLUG]

        tried_slugs = {turn.attack_pattern_slug for turn in prior_turns}
        for pattern in allowed_patterns:
            if pattern.slug not in tried_slugs:
                return pattern

        effectiveness = {
            pattern.slug: max(
                (
                    self._effectiveness_score(turn.outcome)
                    for turn in prior_turns
                    if turn.attack_pattern_slug == pattern.slug
                ),
                default=0,
            )
            for pattern in allowed_patterns
        }
        best_score = max(effectiveness.values())
        candidates = [
            pattern
            for pattern in allowed_patterns
            if effectiveness[pattern.slug] == best_score
        ]
        non_repeating_candidates = [
            pattern
            for pattern in candidates
            if pattern.slug != last_turn.attack_pattern_slug
        ]
        return (non_repeating_candidates or candidates)[0]

    @staticmethod
    def _indicates_partial_compliance(turn: PriorRedAgentTurn) -> bool:
        if turn.outcome is PriorTurnOutcome.PARTIAL_COMPLIANCE:
            return True
        return bool(
            turn.evaluator_feedback
            and "partial compliance" in turn.evaluator_feedback.casefold()
        )

    @staticmethod
    def _effectiveness_score(outcome: PriorTurnOutcome | None) -> int:
        return {
            PriorTurnOutcome.SAFE_REFUSAL: 0,
            PriorTurnOutcome.UNKNOWN: 1,
            None: 1,
            PriorTurnOutcome.PARTIAL_COMPLIANCE: 2,
            PriorTurnOutcome.COMPLIANCE: 3,
        }[outcome]
