from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, JSON, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

JSON_CONFIGURATION = JSON().with_variant(JSONB(), "postgresql")


class PolicyProfile(TimestampMixin, Base):
    __tablename__ = "policy_profiles"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_policy_profiles_slug"),
        CheckConstraint(
            "length(btrim(strictness_level)) > 0",
            name="ck_policy_profiles_strictness_level_nonempty",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    strictness_level: Mapped[str] = mapped_column(String(50), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON_CONFIGURATION,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    duels: Mapped[list[Duel]] = relationship(
        back_populates="policy_profile",
        passive_deletes="all",
    )
