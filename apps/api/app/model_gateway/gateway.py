from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.model_gateway.contracts import ModelGenerationRequest, ModelGenerationResult
from app.model_gateway.exceptions import (
    ModelExecutionError,
    ModelGatewayError,
    ProviderNotConfiguredError,
    ProviderNotSupportedError,
)
from app.model_gateway.provider import ModelProviderAdapter
from app.models.registry import TargetModel

GENERATION_DEFAULT_KEYS = ("temperature", "max_tokens")
RESERVED_CREDENTIAL_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "authorization_header",
        "hf_token",
        "token",
    }
)


def _normalized_key(key: object) -> str:
    return str(key).strip().lower().replace("-", "_")


def _contains_reserved_credentials(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalized_key(key) in RESERVED_CREDENTIAL_KEYS
            or _contains_reserved_credentials(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_reserved_credentials(child) for child in value)
    return False


class ModelGateway:
    """Resolve provider adapters and normalize model execution behavior."""

    def __init__(self, adapters: Mapping[str, ModelProviderAdapter]) -> None:
        self._adapters = {
            provider_type.strip().lower(): adapter
            for provider_type, adapter in adapters.items()
        }

    def resolve_adapter(self, provider_type: str) -> ModelProviderAdapter:
        normalized_type = provider_type.strip().lower()
        try:
            return self._adapters[normalized_type]
        except KeyError as exc:
            raise ProviderNotSupportedError(provider_type) from exc

    async def generate(
        self,
        target_model: TargetModel,
        request: ModelGenerationRequest,
    ) -> ModelGenerationResult:
        provider = target_model.provider
        if provider is None or not provider.is_active:
            provider_type = provider.provider_type if provider is not None else "unknown"
            raise ProviderNotConfiguredError(provider_type)

        provider_type = provider.provider_type
        adapter = self.resolve_adapter(provider_type)
        configuration = target_model.configuration or {}

        if _contains_reserved_credentials(configuration):
            raise ModelExecutionError(
                provider_type,
                "Stored model configuration contains a reserved credential field",
            )

        merged_request = self._merge_generation_defaults(
            provider_type,
            request,
            configuration,
        )

        try:
            return await adapter.generate(
                target_model.canonical_model_id,
                merged_request,
                configuration,
            )
        except ModelGatewayError:
            raise
        except Exception as exc:
            raise ModelExecutionError(provider_type) from exc

    @staticmethod
    def _merge_generation_defaults(
        provider_type: str,
        request: ModelGenerationRequest,
        configuration: Mapping[str, Any],
    ) -> ModelGenerationRequest:
        values = request.model_dump()
        for field_name in GENERATION_DEFAULT_KEYS:
            if values[field_name] is None and field_name in configuration:
                values[field_name] = configuration[field_name]

        try:
            return ModelGenerationRequest.model_validate(values)
        except ValidationError as exc:
            raise ModelExecutionError(
                provider_type,
                "Stored model generation defaults are invalid",
            ) from exc

