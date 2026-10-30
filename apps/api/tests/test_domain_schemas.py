from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import DuelStatus, DuelTurnStatus, ScenarioSeverity
from app.schemas.duels import DuelCreate, DuelTurnCreate
from app.schemas.registry import TargetModelCreate
from app.schemas.scenarios import ScenarioCreate


def scenario_data(severity: str) -> dict[str, object]:
    return {
        "name": "Validation scenario",
        "slug": "validation-scenario",
        "description": "Used only to validate schema behavior.",
        "severity": severity,
        "target_system_prompt": "System prompt",
    }


def duel_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "scenario_id": uuid4(),
        "target_model_id": uuid4(),
        "policy_profile_id": uuid4(),
        "requested_turns": 3,
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("severity", [item.value for item in ScenarioSeverity])
def test_scenario_severity_accepts_supported_values(severity: str) -> None:
    schema = ScenarioCreate.model_validate(scenario_data(severity))
    assert schema.severity.value == severity


@pytest.mark.parametrize("severity", ["informational", "LOW", ""])
def test_scenario_severity_rejects_unsupported_values(severity: str) -> None:
    with pytest.raises(ValidationError):
        ScenarioCreate.model_validate(scenario_data(severity))


@pytest.mark.parametrize("status", [item.value for item in DuelStatus])
def test_duel_status_accepts_supported_values(status: str) -> None:
    schema = DuelCreate.model_validate(duel_data(status=status))
    assert schema.status.value == status


def test_duel_status_rejects_unsupported_values() -> None:
    with pytest.raises(ValidationError):
        DuelCreate.model_validate(duel_data(status="paused"))


@pytest.mark.parametrize("status", [item.value for item in DuelTurnStatus])
def test_turn_status_accepts_supported_values(status: str) -> None:
    schema = DuelTurnCreate(duel_id=uuid4(), turn_number=1, status=status)
    assert schema.status.value == status


def test_turn_status_rejects_unsupported_values() -> None:
    with pytest.raises(ValidationError):
        DuelTurnCreate(duel_id=uuid4(), turn_number=1, status="cancelled")


def test_duel_turn_counts_are_validated() -> None:
    with pytest.raises(ValidationError):
        DuelCreate.model_validate(duel_data(requested_turns=0))

    with pytest.raises(ValidationError):
        DuelCreate.model_validate(duel_data(completed_turns=-1))

    with pytest.raises(ValidationError):
        DuelCreate.model_validate(duel_data(requested_turns=2, completed_turns=3))


def test_turn_number_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        DuelTurnCreate(duel_id=uuid4(), turn_number=0)


@pytest.mark.parametrize("canonical_model_id", ["", "   "])
def test_target_model_requires_canonical_identifier(canonical_model_id: str) -> None:
    with pytest.raises(ValidationError):
        TargetModelCreate(
            provider_id=uuid4(),
            display_name="Target",
            canonical_model_id=canonical_model_id,
            third_party=True,
        )

