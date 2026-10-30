import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest
from huggingface_hub.errors import InferenceTimeoutError

from app.model_gateway.contracts import (
    ModelGenerationRequest,
    ModelMessage,
    ModelRole,
)
from app.model_gateway.exceptions import (
    ModelExecutionError,
    ModelTimeoutError,
    ProviderNotConfiguredError,
)
from app.model_gateway.providers.huggingface import HuggingFaceProviderAdapter


def generation_request() -> ModelGenerationRequest:
    return ModelGenerationRequest(
        messages=[
            ModelMessage(role=ModelRole.SYSTEM, content="Be concise."),
            ModelMessage(role=ModelRole.USER, content="Hello"),
        ],
        temperature=0.3,
        max_tokens=24,
    )


def structured_response() -> SimpleNamespace:
    return SimpleNamespace(
        id="response-id",
        model="organization/model",
        created=123,
        system_fingerprint="provider-version",
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content="Hello from the model"),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=7,
            completion_tokens=5,
            total_tokens=12,
        ),
    )


class MockClient:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.arguments: dict[str, Any] | None = None

    def chat_completion(self, **arguments: Any) -> Any:
        self.arguments = arguments
        if self.error is not None:
            raise self.error
        return self.response


def test_missing_hf_token_prevents_execution() -> None:
    adapter = HuggingFaceProviderAdapter(token=None)

    with pytest.raises(ProviderNotConfiguredError):
        asyncio.run(
            adapter.generate("organization/model", generation_request(), {})
        )


def test_huggingface_health_check_reports_configuration_readiness() -> None:
    unconfigured = HuggingFaceProviderAdapter(token=None)
    configured = HuggingFaceProviderAdapter(token="configured")

    assert not asyncio.run(unconfigured.health_check("organization/model", {}))
    assert asyncio.run(configured.health_check("organization/model", {}))


def test_huggingface_result_and_token_usage_are_normalized() -> None:
    client = MockClient(response=structured_response())
    factory_arguments: dict[str, Any] = {}

    def client_factory(**arguments: Any) -> MockClient:
        factory_arguments.update(arguments)
        return client

    adapter = HuggingFaceProviderAdapter(
        token="configured",
        client_factory=client_factory,
    )
    result = asyncio.run(
        adapter.generate(
            "organization/model",
            generation_request(),
            {"provider_route": "auto"},
        )
    )

    assert factory_arguments["provider"] == "auto"
    assert client.arguments == {
        "messages": [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Hello"},
        ],
        "model": "organization/model",
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 24,
    }
    assert result.content == "Hello from the model"
    assert result.finish_reason == "stop"
    assert result.input_tokens == 7
    assert result.output_tokens == 5
    assert result.total_tokens == 12
    assert result.raw_metadata["provider_route"] == "auto"
    assert "configured" not in result.model_dump_json()


def test_huggingface_failure_is_converted_without_sensitive_details() -> None:
    provider_detail = "provider diagnostic should remain internal"
    client = MockClient(error=RuntimeError(provider_detail))
    adapter = HuggingFaceProviderAdapter(
        token="configured",
        client_factory=lambda **_arguments: client,
    )

    with pytest.raises(ModelExecutionError) as captured:
        asyncio.run(
            adapter.generate("organization/model", generation_request(), {})
        )

    assert provider_detail not in str(captured.value)
    assert isinstance(captured.value.__cause__, RuntimeError)


def test_huggingface_timeout_is_converted() -> None:
    client = MockClient(error=InferenceTimeoutError("provider timed out"))
    adapter = HuggingFaceProviderAdapter(
        token="configured",
        client_factory=lambda **_arguments: client,
    )

    with pytest.raises(ModelTimeoutError):
        asyncio.run(
            adapter.generate("organization/model", generation_request(), {})
        )


def test_huggingface_result_metadata_is_json_serializable() -> None:
    client = MockClient(response=structured_response())
    adapter = HuggingFaceProviderAdapter(
        token="configured",
        client_factory=lambda **_arguments: client,
    )

    result = asyncio.run(
        adapter.generate("organization/model", generation_request(), {})
    )

    json.dumps(result.raw_metadata)
