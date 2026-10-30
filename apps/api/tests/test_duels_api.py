from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.domain.enums import DuelStatus
from app.duels.contracts import DuelCreated, DuelExecutionResult
from app.duels.dependencies import get_duel_orchestrator, get_duel_repository
from app.duels.exceptions import DuelLifecycleError, DuelNotFoundError
from app.main import app

DUEL_ID = uuid4()


def runtime_payload() -> dict[str, object]:
    return {
        "attacker_model": {
            "canonical_model_id": "attacker/model",
            "provider": "mock",
            "third_party": False,
        },
        "judge_model": {
            "canonical_model_id": "judge/model",
            "provider": "mock",
            "third_party": False,
        },
        "target_generation": {"temperature": 0.2, "max_tokens": 128},
    }


def persisted_result(status: DuelStatus = DuelStatus.COMPLETED) -> DuelExecutionResult:
    now = datetime.now(UTC)
    return DuelExecutionResult(
        duel_id=DUEL_ID,
        status=status,
        requested_turns=2,
        completed_turns=2 if status is DuelStatus.COMPLETED else 0,
        turns=[],
        started_at=now,
        completed_at=now if status is not DuelStatus.RUNNING else None,
    )


class RepositoryStub:
    async def create(self, payload):
        return DuelCreated(
            duel_id=DUEL_ID,
            status=DuelStatus.PENDING,
            requested_turns=payload.requested_turns,
            completed_turns=0,
            stop_on_first_breach=payload.stop_on_first_breach,
            created_at=datetime.now(UTC),
        )

    async def get_result(self, duel_id):
        if duel_id != DUEL_ID:
            raise DuelNotFoundError(duel_id)
        return persisted_result()


class OrchestratorStub:
    async def run(self, duel_id, payload):
        assert payload.attacker_model.canonical_model_id == "attacker/model"
        if duel_id != DUEL_ID:
            raise DuelNotFoundError(duel_id)
        return persisted_result()


class DuplicateRunStub:
    async def run(self, duel_id, payload):
        raise DuelLifecycleError("Duel cannot transition from completed to running")


def test_create_pending_duel() -> None:
    app.dependency_overrides[get_duel_repository] = RepositoryStub
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/duels",
                json={
                    "scenario_id": str(uuid4()),
                    "target_model_id": str(uuid4()),
                    "policy_profile_id": str(uuid4()),
                    "requested_turns": 2,
                    "stop_on_first_breach": True,
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["duel_id"] == str(DUEL_ID)


def test_run_pending_duel_with_transient_runtime_configuration() -> None:
    app.dependency_overrides[get_duel_orchestrator] = OrchestratorStub
    try:
        with TestClient(app) as client:
            response = client.post(f"/api/v1/duels/{DUEL_ID}/run", json=runtime_payload())
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert "credential" not in response.text.lower()
    assert "api_key" not in response.text.lower()


def test_fetch_persisted_duel_and_unknown_duel() -> None:
    app.dependency_overrides[get_duel_repository] = RepositoryStub
    try:
        with TestClient(app) as client:
            found = client.get(f"/api/v1/duels/{DUEL_ID}")
            missing = client.get(f"/api/v1/duels/{uuid4()}")
    finally:
        app.dependency_overrides.clear()
    assert found.status_code == 200
    assert found.json()["completed_turns"] == 2
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Duel not found"}


def test_duplicate_run_is_rejected_as_lifecycle_conflict() -> None:
    app.dependency_overrides[get_duel_orchestrator] = DuplicateRunStub
    try:
        with TestClient(app) as client:
            response = client.post(f"/api/v1/duels/{DUEL_ID}/run", json=runtime_payload())
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 409
    assert response.json()["detail"] == "Duel cannot transition from completed to running"


def test_runtime_configuration_rejects_credentials() -> None:
    payload = runtime_payload()
    payload["attacker_model"]["provider_configuration"] = {
        "api_key": "must-not-be-accepted"
    }
    with TestClient(app) as client:
        response = client.post(f"/api/v1/duels/{DUEL_ID}/run", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "provider_configuration"
