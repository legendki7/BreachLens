from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import DuelStatus, DuelTurnStatus, enum_values
from app.models.mixins import TimestampMixin

JSON_EVIDENCE = JSON().with_variant(JSONB(), "postgresql")


class Duel(TimestampMixin, Base):
    __tablename__ = "duels"
    __table_args__ = (
        CheckConstraint("requested_turns > 0", name="ck_duels_requested_turns_positive"),
        CheckConstraint("completed_turns >= 0", name="ck_duels_completed_turns_nonnegative"),
        CheckConstraint(
            "completed_turns <= requested_turns",
            name="ck_duels_completed_turns_not_above_requested",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    scenario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    target_model_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("target_models.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    policy_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("policy_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[DuelStatus] = mapped_column(
        SqlEnum(
            DuelStatus,
            name="duel_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=DuelStatus.PENDING,
        server_default=DuelStatus.PENDING.value,
        index=True,
    )
    requested_turns: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    stop_on_first_breach: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scenario: Mapped[Scenario] = relationship(back_populates="duels")
    target_model: Mapped[TargetModel] = relationship(back_populates="duels")
    policy_profile: Mapped[PolicyProfile] = relationship(back_populates="duels")
    turns: Mapped[list[DuelTurn]] = relationship(
        back_populates="duel",
        passive_deletes="all",
        order_by="DuelTurn.turn_number",
    )


class DuelTurn(TimestampMixin, Base):
    __tablename__ = "duel_turns"
    __table_args__ = (
        UniqueConstraint("duel_id", "turn_number", name="uq_duel_turns_duel_turn_number"),
        CheckConstraint("turn_number > 0", name="ck_duel_turns_turn_number_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    duel_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("duels.id", ondelete="RESTRICT"),
        nullable=False,
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DuelTurnStatus] = mapped_column(
        SqlEnum(
            DuelTurnStatus,
            name="duel_turn_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=DuelTurnStatus.PENDING,
        server_default=DuelTurnStatus.PENDING.value,
        index=True,
    )
    attack_pattern_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attack_patterns.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    attack_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_stage: Mapped[str | None] = mapped_column(String(80), nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    duel: Mapped[Duel] = relationship(back_populates="turns")
    attack_pattern: Mapped[AttackPattern | None] = relationship(back_populates="duel_turns")
    attack_evidence: Mapped[DuelTurnAttack | None] = relationship(
        back_populates="duel_turn",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    model_execution: Mapped[DuelTurnModelExecution | None] = relationship(
        back_populates="duel_turn",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    guardrail_reports: Mapped[list[DuelTurnGuardrailReport]] = relationship(
        back_populates="duel_turn",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    evaluation: Mapped[DuelTurnEvaluation | None] = relationship(
        back_populates="duel_turn",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )


class DuelTurnAttack(TimestampMixin, Base):
    __tablename__ = "duel_turn_attacks"

    duel_turn_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("duel_turns.id", ondelete="CASCADE"),
        primary_key=True,
    )
    attack_pattern_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attack_patterns.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    attack_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    effective_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy_summary: Mapped[str] = mapped_column(Text, nullable=False)
    adaptation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    attacker_model_id: Mapped[str] = mapped_column(String(512), nullable=False)
    attacker_provider: Mapped[str] = mapped_column(String(80), nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON_EVIDENCE, nullable=False, default=dict
    )

    duel_turn: Mapped[DuelTurn] = relationship(back_populates="attack_evidence")


class DuelTurnModelExecution(TimestampMixin, Base):
    __tablename__ = "duel_turn_model_executions"

    duel_turn_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("duel_turns.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_id: Mapped[str] = mapped_column(String(512), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    system_visible_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    latency_ms: Mapped[float] = mapped_column(nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON_EVIDENCE, nullable=False, default=dict
    )

    duel_turn: Mapped[DuelTurn] = relationship(back_populates="model_execution")


class DuelTurnGuardrailReport(TimestampMixin, Base):
    __tablename__ = "duel_turn_guardrail_reports"
    __table_args__ = (
        UniqueConstraint(
            "duel_turn_id", "stage", name="uq_duel_turn_guardrail_reports_turn_stage"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    duel_turn_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("duel_turns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(20), nullable=False)
    final_decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    final_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_latency_ms: Mapped[float] = mapped_column(nullable=False)
    report: Mapped[dict[str, object]] = mapped_column(JSON_EVIDENCE, nullable=False)

    duel_turn: Mapped[DuelTurn] = relationship(back_populates="guardrail_reports")


class DuelTurnEvaluation(TimestampMixin, Base):
    __tablename__ = "duel_turn_evaluations"

    duel_turn_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("duel_turns.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_outcome: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    model_attack_success_score: Mapped[float | None] = mapped_column(nullable=True)
    system_outcome: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    system_attack_success_score: Mapped[float | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    rubric_id: Mapped[str] = mapped_column(String(255), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(80), nullable=False)
    judge_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_model_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    judge_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    evaluation_latency_ms: Mapped[float | None] = mapped_column(nullable=True)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(
        JSON_EVIDENCE, nullable=False, default=list
    )
    evaluation_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON_EVIDENCE, nullable=False, default=dict
    )

    duel_turn: Mapped[DuelTurn] = relationship(back_populates="evaluation")
