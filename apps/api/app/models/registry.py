from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, JSON, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

JSON_CONFIGURATION = JSON().with_variant(JSONB(), "postgresql")


class ModelProvider(TimestampMixin, Base):
    __tablename__ = "model_providers"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_model_providers_slug"),
        CheckConstraint(
            "length(btrim(provider_type)) > 0",
            name="ck_model_providers_provider_type_nonempty",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(80), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    target_models: Mapped[list[TargetModel]] = relationship(
        back_populates="provider",
        passive_deletes="all",
    )


class TargetModel(TimestampMixin, Base):
    __tablename__ = "target_models"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "canonical_model_id",
            name="uq_target_models_provider_canonical_model_id",
        ),
        CheckConstraint(
            "length(btrim(canonical_model_id)) > 0",
            name="ck_target_models_canonical_model_id_nonempty",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("model_providers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_model_id: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_family: Mapped[str | None] = mapped_column(String(255), nullable=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON_CONFIGURATION,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    third_party: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    provider: Mapped[ModelProvider] = relationship(back_populates="target_models")
    duels: Mapped[list[Duel]] = relationship(back_populates="target_model", passive_deletes="all")
