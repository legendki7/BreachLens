from sqlalchemy import CheckConstraint, Enum, JSON, UniqueConstraint
from sqlalchemy.orm import configure_mappers

import app.models  # noqa: F401
from app.db.base import Base
from app.models.duels import (
    Duel,
    DuelTurn,
    DuelTurnAttack,
    DuelTurnEvaluation,
    DuelTurnGuardrailReport,
)
from app.models.policies import PolicyProfile
from app.models.registry import TargetModel
from app.models.scenarios import Scenario


def constraint_names(model: type) -> set[str | None]:
    return {constraint.name for constraint in model.__table__.constraints}


def test_all_models_register_with_shared_metadata() -> None:
    configure_mappers()

    assert set(Base.metadata.tables) == {
        "attack_patterns",
        "duel_turns",
        "duel_turn_attacks",
        "duel_turn_evaluations",
        "duel_turn_guardrail_reports",
        "duel_turn_model_executions",
        "duels",
        "model_providers",
        "policy_profiles",
        "scenario_attack_patterns",
        "scenario_security_risks",
        "scenarios",
        "security_framework_versions",
        "security_frameworks",
        "security_risks",
        "target_models",
    }


def test_scenario_mappings_are_relational() -> None:
    scenario_columns = set(Scenario.__table__.columns.keys())
    assert "attack_patterns" not in scenario_columns
    assert "security_risks" not in scenario_columns
    assert not any(isinstance(column.type, JSON) for column in Scenario.__table__.columns)

    attack_mapping = Base.metadata.tables["scenario_attack_patterns"]
    risk_mapping = Base.metadata.tables["scenario_security_risks"]
    assert set(attack_mapping.columns.keys()) == {"scenario_id", "attack_pattern_id"}
    assert set(risk_mapping.columns.keys()) == {"scenario_id", "security_risk_id"}


def test_important_database_constraints_are_present() -> None:
    assert "uq_target_models_provider_canonical_model_id" in constraint_names(TargetModel)
    assert "uq_duel_turns_duel_turn_number" in constraint_names(DuelTurn)
    assert "ck_duels_requested_turns_positive" in constraint_names(Duel)
    assert "ck_duels_completed_turns_nonnegative" in constraint_names(Duel)
    assert "ck_duel_turns_turn_number_positive" in constraint_names(DuelTurn)

    assert any(isinstance(item, UniqueConstraint) for item in DuelTurn.__table__.constraints)
    assert any(isinstance(item, CheckConstraint) for item in Duel.__table__.constraints)


def test_domain_enums_persist_supported_string_values() -> None:
    assert isinstance(Scenario.__table__.c.severity.type, Enum)
    assert Scenario.__table__.c.severity.type.enums == ["low", "medium", "high", "critical"]
    assert Duel.__table__.c.status.type.enums == [
        "pending",
        "running",
        "completed",
        "stopped",
        "failed",
    ]
    assert DuelTurn.__table__.c.status.type.enums == [
        "pending",
        "generating_attack",
        "scanning_input",
        "awaiting_model",
        "scanning_output",
        "evaluating",
        "completed",
        "failed",
    ]


def test_historical_foreign_keys_are_restrictive() -> None:
    duel_delete_actions = {
        foreign_key.ondelete
        for column in ("scenario_id", "target_model_id", "policy_profile_id")
        for foreign_key in Duel.__table__.c[column].foreign_keys
    }
    turn_delete_actions = {
        foreign_key.ondelete
        for column in ("duel_id", "attack_pattern_id")
        for foreign_key in DuelTurn.__table__.c[column].foreign_keys
    }

    assert duel_delete_actions == {"RESTRICT"}
    assert turn_delete_actions == {"RESTRICT"}


def test_json_is_limited_to_flexible_configuration() -> None:
    assert isinstance(PolicyProfile.__table__.c.configuration.type, JSON)
    assert isinstance(TargetModel.__table__.c.configuration.type, JSON)
    assert isinstance(DuelTurnAttack.__table__.c.metadata.type, JSON)
    assert isinstance(DuelTurnGuardrailReport.__table__.c.report.type, JSON)
    assert isinstance(DuelTurnEvaluation.__table__.c.evidence.type, JSON)


def test_phase_8_evidence_constraints_and_analytics_columns() -> None:
    assert DuelTurnAttack.__table__.primary_key.columns.keys() == ["duel_turn_id"]
    assert DuelTurnEvaluation.__table__.primary_key.columns.keys() == ["duel_turn_id"]
    assert (
        "uq_duel_turn_guardrail_reports_turn_stage"
        in constraint_names(DuelTurnGuardrailReport)
    )
    assert {
        "model_outcome",
        "model_attack_success_score",
        "system_outcome",
        "system_attack_success_score",
        "rubric_id",
        "rubric_version",
    }.issubset(DuelTurnEvaluation.__table__.columns.keys())

    evidence_foreign_keys = {
        foreign_key.ondelete
        for model in (
            DuelTurnAttack,
            DuelTurnEvaluation,
            DuelTurnGuardrailReport,
        )
        for foreign_key in model.__table__.c.duel_turn_id.foreign_keys
    }
    assert evidence_foreign_keys == {"CASCADE"}
