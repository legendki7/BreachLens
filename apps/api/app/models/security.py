from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class SecurityFramework(TimestampMixin, Base):
    __tablename__ = "security_frameworks"
    __table_args__ = (UniqueConstraint("slug", name="uq_security_frameworks_slug"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    versions: Mapped[list[SecurityFrameworkVersion]] = relationship(
        back_populates="framework",
        passive_deletes="all",
    )


class SecurityFrameworkVersion(TimestampMixin, Base):
    __tablename__ = "security_framework_versions"
    __table_args__ = (
        UniqueConstraint(
            "framework_id",
            "version",
            name="uq_security_framework_versions_framework_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    framework_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("security_frameworks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")

    framework: Mapped[SecurityFramework] = relationship(back_populates="versions")
    risks: Mapped[list[SecurityRisk]] = relationship(
        back_populates="framework_version",
        passive_deletes="all",
    )


class SecurityRisk(TimestampMixin, Base):
    __tablename__ = "security_risks"
    __table_args__ = (
        UniqueConstraint(
            "framework_version_id",
            "code",
            name="uq_security_risks_framework_version_code",
        ),
        CheckConstraint("sort_order >= 0", name="ck_security_risks_sort_order_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    framework_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("security_framework_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    framework_version: Mapped[SecurityFrameworkVersion] = relationship(back_populates="risks")
    scenario_links: Mapped[list[ScenarioSecurityRisk]] = relationship(
        back_populates="security_risk",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
