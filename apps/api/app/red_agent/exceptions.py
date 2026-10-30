class RedAgentError(RuntimeError):
    """Base error for Red Agent planning and generation failures."""


class ScenarioAttackPatternsUnavailableError(RedAgentError):
    def __init__(self, scenario_slug: str) -> None:
        self.scenario_slug = scenario_slug
        super().__init__(
            f"Scenario '{scenario_slug}' has no configured attack patterns"
        )


class InvalidAttackPatternError(RedAgentError):
    def __init__(self, pattern_slug: str, scenario_slug: str) -> None:
        self.pattern_slug = pattern_slug
        self.scenario_slug = scenario_slug
        super().__init__(
            f"Attack pattern '{pattern_slug}' is not allowed for scenario "
            f"'{scenario_slug}'"
        )


class RedAgentGenerationError(RedAgentError):
    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__("Red Agent generation failed")


class RedAgentOutputValidationError(RedAgentError):
    def __init__(self) -> None:
        super().__init__("Attacker model returned invalid structured output")


class RedAgentObjectiveFidelityError(RedAgentOutputValidationError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__()
