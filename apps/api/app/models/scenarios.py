from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import Boolean, Enum as SqlEnum, ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import ScenarioSeverity, enum_values
from app.models.mixins import TimestampMixin


class AttackPattern(TimestampMixin, Base):
    __tablename__ = "attack_patterns"
    __table_args__ = (UniqueConstraint("slug", name="uq_attack_patterns_slug"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)

    scenario_links: Mapped[list[ScenarioAttackPattern]] = relationship(
        back_populates="attack_pattern",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    duel_turns: Mapped[list[DuelTurn]] = relationship(
        back_populates="attack_pattern",
        passive_deletes="all",
    )


class Scenario(TimestampMixin, Base):
    __tablename__ = "scenarios"
    __table_args__ = (UniqueConstraint("slug", name="uq_scenarios_slug"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[ScenarioSeverity] = mapped_column(
        SqlEnum(
            ScenarioSeverity,
            name="scenario_severity",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    target_system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    attack_pattern_links: Mapped[list[ScenarioAttackPattern]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    security_risk_links: Mapped[list[ScenarioSecurityRisk]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    duels: Mapped[list[Duel]] = relationship(back_populates="scenario", passive_deletes="all")


class ScenarioAttackPattern(Base):
    __tablename__ = "scenario_attack_patterns"
    __table_args__ = (Index("ix_scenario_attack_patterns_attack_pattern_id", "attack_pattern_id"),)

    scenario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    attack_pattern_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attack_patterns.id", ondelete="CASCADE"),
        primary_key=True,
    )

    scenario: Mapped[Scenario] = relationship(back_populates="attack_pattern_links")
    attack_pattern: Mapped[AttackPattern] = relationship(back_populates="scenario_links")


class ScenarioSecurityRisk(Base):
    __tablename__ = "scenario_security_risks"
    __table_args__ = (Index("ix_scenario_security_risks_security_risk_id", "security_risk_id"),)

    scenario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    security_risk_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("security_risks.id", ondelete="CASCADE"),
        primary_key=True,
    )

    scenario: Mapped[Scenario] = relationship(back_populates="security_risk_links")
    security_risk: Mapped[SecurityRisk] = relationship(back_populates="scenario_links")
