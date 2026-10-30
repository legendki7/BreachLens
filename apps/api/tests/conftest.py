"""Explicit synthetic database configuration for unit tests; no real database."""

import pytest

_environment = pytest.MonkeyPatch()


def pytest_configure() -> None:
    # Set before test modules import the API and construct its lazy DB engine.
    _environment.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://synthetic_user:synthetic_password@db.invalid/test",
    )


def pytest_unconfigure() -> None:
    _environment.undo()
