import pytest
from pydantic import ValidationError

from app.model_gateway.contracts import (
    ModelGenerationRequest,
    ModelMessage,
    ModelRole,
)


@pytest.mark.parametrize("role", [item.value for item in ModelRole])
def test_model_message_accepts_supported_roles(role: str) -> None:
    message = ModelMessage(role=role, content="Hello")
    assert message.role.value == role


def test_generation_request_rejects_empty_messages() -> None:
    with pytest.raises(ValidationError):
        ModelGenerationRequest(messages=[])


@pytest.mark.parametrize("content", ["", "   "])
def test_model_message_rejects_blank_content(content: str) -> None:
    with pytest.raises(ValidationError):
        ModelMessage(role=ModelRole.USER, content=content)


@pytest.mark.parametrize("temperature", [-0.01, 2.01])
def test_generation_request_rejects_invalid_temperature(temperature: float) -> None:
    with pytest.raises(ValidationError):
        ModelGenerationRequest(
            messages=[ModelMessage(role=ModelRole.USER, content="Hello")],
            temperature=temperature,
        )


@pytest.mark.parametrize("max_tokens", [0, -1])
def test_generation_request_rejects_invalid_max_tokens(max_tokens: int) -> None:
    with pytest.raises(ValidationError):
        ModelGenerationRequest(
            messages=[ModelMessage(role=ModelRole.USER, content="Hello")],
            max_tokens=max_tokens,
        )

