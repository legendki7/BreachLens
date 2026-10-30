from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.model_gateway.contracts import ModelGenerationResult
from app.model_gateway.dependencies import get_model_gateway
from app.model_gateway.exceptions import ProviderNotConfiguredError
from app.models.registry import ModelProvider, TargetModel


class ScalarResult:
    def __init__(self, value: TargetModel | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> TargetModel | None:
        return self.value


class ModelSession:
    def __init__(self, target_model: TargetModel | None) -> None:
        self.target_model = target_model

    async def execute(self, _query: object) -> ScalarResult:
        return ScalarResult(self.target_model)


class SuccessfulGateway:
    def __init__(self) -> None:
        self.request: Any = None

    async def generate(self, target_model: TargetModel, request: Any) -> ModelGenerationResult:
        self.request = request
        return ModelGenerationResult(
            content="Model response",
            model_id=target_model.canonical_model_id,
            provider=target_model.provider.provider_type,
            latency_ms=2,
        )


class UnconfiguredGateway:
    async def generate(self, _target_model: TargetModel, _request: Any) -> None:
        raise ProviderNotConfiguredError("huggingface")


def target_model(*, active: bool = True) -> TargetModel:
    provider = ModelProvider(
        id=uuid4(),
        name="Hugging Face",
        slug="hugging-face",
        provider_type="huggingface",
        is_active=True,
    )
    return TargetModel(
        id=uuid4(),
        provider=provider,
        provider_id=provider.id,
        display_name="Target",
        canonical_model_id="organization/model",
        configuration={},
        third_party=True,
        is_active=active,
    )


def override_session(session: ModelSession):
    async def dependency() -> AsyncIterator[ModelSession]:
        yield session

    return dependency


def test_model_test_endpoint_calls_gateway_with_registered_target() -> None:
    target = target_model()
    gateway = SuccessfulGateway()
    app.dependency_overrides[get_db] = override_session(ModelSession(target))
    app.dependency_overrides[get_model_gateway] = lambda: gateway
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/models/test",
                json={
                    "target_model_id": str(target.id),
                    "system_message": "Be concise.",
                    "user_message": "Hello",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["content"] == "Model response"
    assert [message.role.value for message in gateway.request.messages] == ["system", "user"]


def test_model_test_endpoint_rejects_inactive_target() -> None:
    target = target_model(active=False)
    app.dependency_overrides[get_db] = override_session(ModelSession(target))
    app.dependency_overrides[get_model_gateway] = SuccessfulGateway
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/models/test",
                json={"target_model_id": str(target.id), "user_message": "Hello"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409


def test_model_test_endpoint_maps_missing_provider_configuration() -> None:
    target = target_model()
    app.dependency_overrides[get_db] = override_session(ModelSession(target))
    app.dependency_overrides[get_model_gateway] = UnconfiguredGateway
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/models/test",
                json={"target_model_id": str(target.id), "user_message": "Hello"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Target model provider is not configured"}

