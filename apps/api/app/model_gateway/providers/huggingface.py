import asyncio
from collections.abc import Callable, Mapping
from functools import partial
from time import perf_counter
from typing import Any

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

from app.model_gateway.contracts import ModelGenerationRequest, ModelGenerationResult
from app.model_gateway.exceptions import (
    ModelExecutionError,
    ModelGatewayError,
    ModelTimeoutError,
    ProviderNotConfiguredError,
)
from app.model_gateway.provider import ModelProviderAdapter

HUGGING_FACE_PROVIDER_TYPE = "huggingface"
DEFAULT_PROVIDER_ROUTE = "auto"
DEFAULT_TIMEOUT_SECONDS = 30.0


class HuggingFaceProviderAdapter(ModelProviderAdapter):
    provider_type = HUGGING_FACE_PROVIDER_TYPE

    def __init__(
        self,
        token: str | None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        client_factory: Callable[..., Any] = InferenceClient,
    ) -> None:
        self._token = token.strip() if token else None
        self._timeout_seconds = timeout_seconds
        self._client_factory = client_factory

    async def health_check(
        self,
        model_id: str,
        configuration: Mapping[str, Any],
    ) -> bool:
        self._provider_route(configuration)
        return self._token is not None and bool(model_id.strip())

    async def generate(
        self,
        model_id: str,
        request: ModelGenerationRequest,
        configuration: Mapping[str, Any],
    ) -> ModelGenerationResult:
        if self._token is None:
            raise ProviderNotConfiguredError(self.provider_type)

        provider_route = self._provider_route(configuration)
        started_at = perf_counter()

        try:
            client = self._client_factory(
                provider=provider_route,
                token=self._token,
                timeout=self._timeout_seconds,
            )
            request_arguments: dict[str, Any] = {
                "messages": [message.model_dump(mode="json") for message in request.messages],
                "model": model_id,
                "stream": False,
            }
            if request.temperature is not None:
                request_arguments["temperature"] = request.temperature
            if request.max_tokens is not None:
                request_arguments["max_tokens"] = request.max_tokens

            response = await asyncio.to_thread(
                partial(client.chat_completion, **request_arguments)
            )
            latency_ms = (perf_counter() - started_at) * 1000
            return self._normalize_result(
                response,
                model_id=model_id,
                provider_route=provider_route,
                latency_ms=latency_ms,
            )
        except (InferenceTimeoutError, TimeoutError) as exc:
            raise ModelTimeoutError(self.provider_type) from exc
        except ModelGatewayError:
            raise
        except HfHubHTTPError as exc:
            raise ModelExecutionError(self.provider_type) from exc
        except Exception as exc:
            raise ModelExecutionError(self.provider_type) from exc

    def _provider_route(self, configuration: Mapping[str, Any]) -> str:
        value = configuration.get("provider_route", DEFAULT_PROVIDER_ROUTE)
        if not isinstance(value, str) or not value.strip():
            raise ModelExecutionError(
                self.provider_type,
                "Hugging Face provider route configuration is invalid",
            )
        return value.strip()

    def _normalize_result(
        self,
        response: Any,
        *,
        model_id: str,
        provider_route: str,
        latency_ms: float,
    ) -> ModelGenerationResult:
        choices = getattr(response, "choices", None)
        if not choices:
            raise ModelExecutionError(self.provider_type)

        choice = choices[0]
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str):
            raise ModelExecutionError(self.provider_type)

        usage = getattr(response, "usage", None)
        raw_metadata: dict[str, Any] = {"provider_route": provider_route}
        for result_key, attribute_name in (
            ("response_id", "id"),
            ("response_model_id", "model"),
            ("created", "created"),
            ("system_fingerprint", "system_fingerprint"),
        ):
            value = getattr(response, attribute_name, None)
            if isinstance(value, (str, int, float, bool)):
                raw_metadata[result_key] = value

        finish_reason = getattr(choice, "finish_reason", None)
        return ModelGenerationResult(
            content=content,
            model_id=model_id,
            provider=self.provider_type,
            finish_reason=str(finish_reason) if finish_reason is not None else None,
            input_tokens=self._optional_integer(usage, "prompt_tokens"),
            output_tokens=self._optional_integer(usage, "completion_tokens"),
            total_tokens=self._optional_integer(usage, "total_tokens"),
            latency_ms=latency_ms,
            raw_metadata=raw_metadata,
        )

    @staticmethod
    def _optional_integer(value: Any, attribute_name: str) -> int | None:
        candidate = getattr(value, attribute_name, None)
        return candidate if isinstance(candidate, int) and candidate >= 0 else None

