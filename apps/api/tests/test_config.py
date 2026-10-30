import pytest
from pydantic import ValidationError

from app.core.config import DatabaseSettings, Settings


def test_configuration_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # Synthetic parsing fixture only; no database connection is attempted.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db/test")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3100,https://arena.example")
    monkeypatch.setenv("APP_ENV", "test")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+asyncpg://user:pass@db/test"
    assert settings.api_port == 9000
    assert settings.frontend_origins == [
        "http://localhost:3100",
        "https://arena.example",
    ]
    assert settings.app_env == "test"


def test_configuration_rejects_wildcard_cors_origin() -> None:
    with pytest.raises(ValidationError):
        Settings(frontend_url="*", _env_file=None)


def test_database_free_tools_do_not_require_database_url(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert Settings(_env_file=None).database_url is None


def test_database_backed_settings_require_database_url(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError) as error:
        DatabaseSettings(_env_file=None)
    assert error.value.errors()[0]["loc"] == ("database_url",)
    assert error.value.errors()[0]["type"] == "missing"


@pytest.mark.parametrize("value", ["", "   "])
def test_database_backed_settings_reject_blank_url(monkeypatch, value) -> None:
    monkeypatch.setenv("DATABASE_URL", value)
    with pytest.raises(ValidationError):
        DatabaseSettings(_env_file=None)


def test_database_environment_overrides_dotenv(monkeypatch, tmp_path) -> None:
    # Synthetic parsing fixtures only; neither endpoint is contacted.
    path = tmp_path / ".env"
    file_url = "postgresql+asyncpg://fixture:file_password@file.invalid/test"
    process_url = "postgresql+asyncpg://fixture:process_password@process.invalid/test"
    path.write_text(f"DATABASE_URL={file_url}\n", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert DatabaseSettings(_env_file=path).database_url == file_url
    monkeypatch.setenv("DATABASE_URL", process_url)
    assert DatabaseSettings(_env_file=path).database_url == process_url
    assert DatabaseSettings(database_url=file_url, _env_file=path).database_url == file_url

