class GuardrailError(RuntimeError):
    """Base error for defensive guardrail failures."""


class GuardrailConfigurationError(GuardrailError):
    pass


class GuardrailExecutionError(GuardrailError):
    def __init__(self, adapter: str, message: str = "Guardrail execution failed") -> None:
        self.adapter = adapter
        super().__init__(message)


class GuardrailAdapterUnavailableError(GuardrailError):
    def __init__(self, adapter: str) -> None:
        self.adapter = adapter
        super().__init__(f"Guardrail adapter '{adapter}' is unavailable")


class UnsupportedGuardrailStageError(GuardrailError):
    def __init__(self, stage: object) -> None:
        self.stage = stage
        super().__init__("Guardrail stage is unsupported")
