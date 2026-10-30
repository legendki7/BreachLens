"""Provider-independent model execution boundary."""

from app.model_gateway.contracts import (
    ModelGenerationRequest,
    ModelGenerationResult,
    ModelMessage,
    ModelRole,
)
from app.model_gateway.exceptions import (
    ModelExecutionError,
    ModelGatewayError,
    ModelTimeoutError,
    ProviderNotConfiguredError,
    ProviderNotSupportedError,
)
from app.model_gateway.gateway import ModelGateway

__all__ = [
    "ModelExecutionError",
    "ModelGateway",
    "ModelGatewayError",
    "ModelGenerationRequest",
    "ModelGenerationResult",
    "ModelMessage",
    "ModelRole",
    "ModelTimeoutError",
    "ProviderNotConfiguredError",
    "ProviderNotSupportedError",
]

