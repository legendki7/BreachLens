class EvaluationError(RuntimeError):
    """Base error for evidence analysis and rubric judgment."""


class RubricNotFoundError(EvaluationError):
    def __init__(self, scenario_slug: str) -> None:
        self.scenario_slug = scenario_slug
        super().__init__(f"No rubric exists for scenario '{scenario_slug}'")


class RubricConfigurationError(EvaluationError):
    pass


class JudgeGenerationError(EvaluationError):
    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__("Judge model generation failed")


class JudgeOutputValidationError(EvaluationError):
    def __init__(self) -> None:
        super().__init__("Judge model returned invalid structured output")


class EvaluationInconclusiveError(EvaluationError):
    pass
