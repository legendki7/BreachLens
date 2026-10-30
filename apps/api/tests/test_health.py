from collections.abc import AsyncIterator

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


class SuccessfulSession:
    async def execute(self, _statement: object) -> None:
        return None


class UnavailableSession:
    async def execute(self, _statement: object) -> None:
        raise OperationalError("SELECT 1", {}, OSError("database unavailable"))


def override_session(session: object):
    async def dependency() -> AsyncIterator[object]:
        yield session

    return dependency


def test_api_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "red-team-arena-api",
    }


def test_database_health_when_database_is_available() -> None:
    app.dependency_overrides[get_db] = override_session(SuccessfulSession())
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/health/database")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "postgresql"}


def test_database_health_when_database_is_unavailable() -> None:
    app.dependency_overrides[get_db] = override_session(UnavailableSession())
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/health/database")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "error", "service": "postgresql"}

