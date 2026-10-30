import argparse
import asyncio
from collections.abc import Mapping
import re
import sys
from typing import Any

from huggingface_hub.errors import HfHubHTTPError

from app.core.config import get_settings
from app.model_gateway.contracts import (
    ModelGenerationRequest,
    ModelMessage,
    ModelRole,
)
from app.model_gateway.exceptions import ModelGatewayError
from app.model_gateway.gateway import ModelGateway
from app.model_gateway.providers.huggingface import (
    HUGGING_FACE_PROVIDER_TYPE,
    HuggingFaceProviderAdapter,
)
from app.models.registry import ModelProvider, TargetModel

MAX_DIAGNOSTIC_VALUE_LENGTH = 300
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[^\s,;]+")
_HF_TOKEN_PATTERN = re.compile(r"\bhf_[A-Za-z0-9_-]+\b")
_CREDENTIAL_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|authorization|hf[_-]?token|password|secret|token)"
    r"\s*[:=]\s*['\"]?[^\s,'\";}]+"
)
_URL_WITH_QUERY_PATTERN = re.compile(r"https?://[^\s<>\"']*\?[^\s<>\"']*")


def _sanitize_diagnostic_value(value: object) -> str:
    text = str(value)
    text = _BEARER_PATTERN.sub("Bearer [REDACTED]", text)
    text = _HF_TOKEN_PATTERN.sub("[REDACTED]", text)
    text = _CREDENTIAL_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        text,
    )
    text = _URL_WITH_QUERY_PATTERN.sub(
        lambda match: f"{match.group(0).split('?', 1)[0]}?[REDACTED]",
        text,
    )
    if len(text) > MAX_DIAGNOSTIC_VALUE_LENGTH:
        return f"{text[:MAX_DIAGNOSTIC_VALUE_LENGTH]}…"
    return text


def _exception_chain(error: BaseException) -> tuple[BaseException, ...]:
    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        current = current.__cause__ or current.__context__
    return tuple(chain)


def _safe_http_diagnostics(error: HfHubHTTPError) -> dict[str, str]:
    diagnostics: dict[str, str] = {}
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        diagnostics["HTTP status"] = str(status_code)

    payload: Any = None
    if response is not None:
        try:
            payload = response.json()
        except Exception:
            payload = None
    if isinstance(payload, Mapping):
        for field in ("error", "message", "error_code"):
            value = payload.get(field)
            if isinstance(value, (str, int, float, bool)):
                diagnostics[f"Provider {field}"] = _sanitize_diagnostic_value(value)

    if "Provider message" not in diagnostics:
        server_message = getattr(error, "server_message", None)
        if isinstance(server_message, str) and server_message.strip():
            diagnostics["Provider message"] = _sanitize_diagnostic_value(
                server_message
            )
    return diagnostics


def _print_safe_failure_diagnostics(
    error: ModelGatewayError,
    *,
    provider_route: str,
    model_id: str,
) -> None:
    chain = _exception_chain(error)
    http_error = next(
        (item for item in chain if isinstance(item, HfHubHTTPError)),
        None,
    )
    original = http_error or chain[-1]
    print(f"Original exception type: {type(original).__name__}", file=sys.stderr)
    if http_error is not None:
        for label, value in _safe_http_diagnostics(http_error).items():
            print(f"{label}: {value}", file=sys.stderr)
    print(f"Provider route: {_sanitize_diagnostic_value(provider_route)}", file=sys.stderr)
    print(f"Model ID: {_sanitize_diagnostic_value(model_id)}", file=sys.stderr)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Perform one explicit Hugging Face chat-completion request.",
    )
    parser.add_argument("model_id", help="Canonical Hugging Face model identifier")
    parser.add_argument("--message", required=True, help="Single user message")
    parser.add_argument("--system", help="Optional system message")
    parser.add_argument(
        "--provider-route",
        default="auto",
        help="Hugging Face Inference Provider route (default: auto)",
    )
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--max-tokens", type=int)
    return parser.parse_args()


async def run() -> int:
    arguments = parse_arguments()
    settings = get_settings()
    if not settings.hf_token:
        print("HF_TOKEN is required for real Hugging Face inference.", file=sys.stderr)
        return 2

    provider = ModelProvider(
        name="Hugging Face",
        slug="hugging-face-runtime-check",
        provider_type=HUGGING_FACE_PROVIDER_TYPE,
        is_active=True,
    )
    target_model = TargetModel(
        provider=provider,
        display_name=arguments.model_id,
        canonical_model_id=arguments.model_id,
        configuration={"provider_route": arguments.provider_route},
        third_party=True,
        is_active=True,
    )
    gateway = ModelGateway(
        {
            HUGGING_FACE_PROVIDER_TYPE: HuggingFaceProviderAdapter(
                token=settings.hf_token,
            )
        }
    )

    messages: list[ModelMessage] = []
    if arguments.system:
        messages.append(ModelMessage(role=ModelRole.SYSTEM, content=arguments.system))
    messages.append(ModelMessage(role=ModelRole.USER, content=arguments.message))

    print(f"Testing model: {arguments.model_id}")
    try:
        result = await gateway.generate(
            target_model,
            ModelGenerationRequest(
                messages=messages,
                temperature=arguments.temperature,
                max_tokens=arguments.max_tokens,
            ),
        )
    except ModelGatewayError as exc:
        _print_safe_failure_diagnostics(
            exc,
            provider_route=arguments.provider_route,
            model_id=arguments.model_id,
        )
        return 1

    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
