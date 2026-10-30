class ModelGatewayError(RuntimeError):
    """Base error for failures crossing the model execution boundary."""

    def __init__(self, provider_type: str, message: str) -> None:
        self.provider_type = provider_type
        super().__init__(message)


class ProviderNotSupportedError(ModelGatewayError):
    def __init__(self, provider_type: str) -> None:
        super().__init__(provider_type, f"Model provider '{provider_type}' is not supported")


class ProviderNotConfiguredError(ModelGatewayError):
    def __init__(self, provider_type: str) -> None:
        super().__init__(provider_type, f"Model provider '{provider_type}' is not configured")


class ModelExecutionError(ModelGatewayError):
    def __init__(self, provider_type: str, message: str = "Model execution failed") -> None:
        super().__init__(provider_type, message)


class ModelTimeoutError(ModelExecutionError):
    def __init__(self, provider_type: str) -> None:
        super().__init__(provider_type, "Model execution timed out")

