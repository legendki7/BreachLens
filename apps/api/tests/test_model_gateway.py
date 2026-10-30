import asyncio
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import pytest

from app.model_gateway.contracts import (
    ModelGenerationRequest,
    ModelGenerationResult,
    ModelMessage,
    ModelRole,
)
from app.model_gateway.exceptions import ModelExecutionError, ProviderNotSupportedError
from app.model_gateway.gateway import ModelGateway
from app.model_gateway.provider import ModelProviderAdapter
from app.models.registry import ModelProvider, TargetModel


class RecordingAdapter(ModelProviderAdapter):
    provider_type = "recording"

    def __init__(self) -> None:
        self.called = False
        self.request: ModelGenerationRequest | None = None
        self.configuration: Mapping[str, Any] | None = None

    async def generate(
        self,
        model_id: str,
        request: ModelGenerationRequest,
        configuration: Mapping[str, Any],
    ) -> ModelGenerationResult:
        self.called = True
        self.request = request
        self.configuration = configuration
        return ModelGenerationResult(
            content="Normalized output",
            model_id=model_id,
            provider=self.provider_type,
            latency_ms=1,
        )

    async def health_check(
        self,
        model_id: str,
        configuration: Mapping[str, Any],
    ) -> bool:
        return bool(model_id)


def make_target(configuration: dict[str, Any] | None = None) -> TargetModel:
    provider = ModelProvider(
        id=uuid4(),
        name="Recording Provider",
        slug="recording-provider",
        provider_type="recording",
        is_active=True,
    )
    return TargetModel(
        id=uuid4(),
        provider=provider,
        provider_id=provider.id,
        display_name="Target",
        canonical_model_id="organization/model",
        configuration=configuration or {},
        third_party=True,
        is_active=True,
    )


def request() -> ModelGenerationRequest:
    return ModelGenerationRequest(
        messages=[ModelMessage(role=ModelRole.USER, content="Hello")]
    )


def test_gateway_resolves_adapter_and_merges_safe_defaults() -> None:
    adapter = RecordingAdapter()
    gateway = ModelGateway({"recording": adapter})
    target = make_target({"temperature": 0.4, "max_tokens": 32, "provider_route": "auto"})

    result = asyncio.run(gateway.generate(target, request()))

    assert result.content == "Normalized output"
    assert adapter.request is not None
    assert adapter.request.temperature == 0.4
    assert adapter.request.max_tokens == 32
    assert adapter.configuration == target.configuration


def test_gateway_rejects_unsupported_provider() -> None:
    target = make_target()
    target.provider.provider_type = "unsupported"

    with pytest.raises(ProviderNotSupportedError):
        asyncio.run(ModelGateway({}).generate(target, request()))


def test_gateway_rejects_stored_credentials_without_exposing_them() -> None:
    credential_value = "credential-value-must-not-escape"
    adapter = RecordingAdapter()
    gateway = ModelGateway({"recording": adapter})
    target = make_target({"nested": {"api_key": credential_value}})

    with pytest.raises(ModelExecutionError) as captured:
        asyncio.run(gateway.generate(target, request()))

    assert credential_value not in str(captured.value)
    assert not adapter.called

