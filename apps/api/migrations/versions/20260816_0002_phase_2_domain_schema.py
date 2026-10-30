"""Add the Phase 2 domain schema.

Revision ID: 20260816_0002
Revises: 20260814_0001
Create Date: 2026-08-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260816_0002"
down_revision: str | None = "20260814_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

scenario_severity = postgresql.ENUM(
    "low",
    "medium",
    "high",
    "critical",
    name="scenario_severity",
    create_type=False,
)
duel_status = postgresql.ENUM(
    "pending",
    "running",
    "completed",
    "stopped",
    "failed",
    name="duel_status",
    create_type=False,
)
duel_turn_status = postgresql.ENUM(
    "pending",
    "generating_attack",
    "scanning_input",
    "awaiting_model",
    "scanning_output",
    "evaluating",
    "completed",
    "failed",
    name="duel_turn_status",
    create_type=False,
)


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    bind = op.get_bind()
    scenario_severity.create(bind, checkfirst=True)
    duel_status.create(bind, checkfirst=True)
    duel_turn_status.create(bind, checkfirst=True)

    op.create_table(
        "security_frameworks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_security_frameworks_slug"),
    )
    op.create_table(
        "security_framework_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("framework_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["framework_id"],
            ["security_frameworks.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "framework_id",
            "version",
            name="uq_security_framework_versions_framework_version",
        ),
    )
    op.create_index(
        "ix_security_framework_versions_framework_id",
        "security_framework_versions",
        ["framework_id"],
    )
    op.create_table(
        "security_risks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("framework_version_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_security_risks_sort_order_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["framework_version_id"],
            ["security_framework_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "framework_version_id",
            "code",
            name="uq_security_risks_framework_version_code",
        ),
    )
    op.create_index(
        "ix_security_risks_framework_version_id",
        "security_risks",
        ["framework_version_id"],
    )
    op.create_table(
        "attack_patterns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_attack_patterns_slug"),
    )
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", scenario_severity, nullable=False),
        sa.Column("target_system_prompt", sa.Text(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_scenarios_slug"),
    )
    op.create_table(
        "scenario_attack_patterns",
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("attack_pattern_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["attack_pattern_id"],
            ["attack_patterns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("scenario_id", "attack_pattern_id"),
    )
    op.create_index(
        "ix_scenario_attack_patterns_attack_pattern_id",
        "scenario_attack_patterns",
        ["attack_pattern_id"],
    )
    op.create_table(
        "scenario_security_risks",
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("security_risk_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["security_risk_id"],
            ["security_risks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("scenario_id", "security_risk_id"),
    )
    op.create_index(
        "ix_scenario_security_risks_security_risk_id",
        "scenario_security_risks",
        ["security_risk_id"],
    )
    op.create_table(
        "policy_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("strictness_level", sa.String(length=50), nullable=False),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_builtin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "length(btrim(strictness_level)) > 0",
            name="ck_policy_profiles_strictness_level_nonempty",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_policy_profiles_slug"),
    )
    op.create_table(
        "model_providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("provider_type", sa.String(length=80), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "length(btrim(provider_type)) > 0",
            name="ck_model_providers_provider_type_nonempty",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_model_providers_slug"),
    )
    op.create_table(
        "target_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("canonical_model_id", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("model_family", sa.String(length=255), nullable=True),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("third_party", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "length(btrim(canonical_model_id)) > 0",
            name="ck_target_models_canonical_model_id_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["model_providers.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_id",
            "canonical_model_id",
            name="uq_target_models_provider_canonical_model_id",
        ),
    )
    op.create_table(
        "duels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("target_model_id", sa.Uuid(), nullable=False),
        sa.Column("policy_profile_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            duel_status,
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("requested_turns", sa.Integer(), nullable=False),
        sa.Column("completed_turns", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "stop_on_first_breach",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint(
            "completed_turns <= requested_turns",
            name="ck_duels_completed_turns_not_above_requested",
        ),
        sa.CheckConstraint(
            "completed_turns >= 0",
            name="ck_duels_completed_turns_nonnegative",
        ),
        sa.CheckConstraint(
            "requested_turns > 0",
            name="ck_duels_requested_turns_positive",
        ),
        sa.ForeignKeyConstraint(
            ["policy_profile_id"],
            ["policy_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_model_id"],
            ["target_models.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_duels_policy_profile_id", "duels", ["policy_profile_id"])
    op.create_index("ix_duels_scenario_id", "duels", ["scenario_id"])
    op.create_index("ix_duels_status", "duels", ["status"])
    op.create_index("ix_duels_target_model_id", "duels", ["target_model_id"])
    op.create_table(
        "duel_turns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("duel_id", sa.Uuid(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            duel_turn_status,
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("attack_pattern_id", sa.Uuid(), nullable=True),
        sa.Column("attack_prompt", sa.Text(), nullable=True),
        sa.Column("target_response", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint(
            "turn_number > 0",
            name="ck_duel_turns_turn_number_positive",
        ),
        sa.ForeignKeyConstraint(
            ["attack_pattern_id"],
            ["attack_patterns.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["duel_id"],
            ["duels.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "duel_id",
            "turn_number",
            name="uq_duel_turns_duel_turn_number",
        ),
    )
    op.create_index(
        "ix_duel_turns_attack_pattern_id",
        "duel_turns",
        ["attack_pattern_id"],
    )
    op.create_index("ix_duel_turns_status", "duel_turns", ["status"])


def downgrade() -> None:
    op.drop_index("ix_duel_turns_status", table_name="duel_turns")
    op.drop_index("ix_duel_turns_attack_pattern_id", table_name="duel_turns")
    op.drop_table("duel_turns")

    op.drop_index("ix_duels_target_model_id", table_name="duels")
    op.drop_index("ix_duels_status", table_name="duels")
    op.drop_index("ix_duels_scenario_id", table_name="duels")
    op.drop_index("ix_duels_policy_profile_id", table_name="duels")
    op.drop_table("duels")

    op.drop_table("target_models")
    op.drop_table("model_providers")
    op.drop_table("policy_profiles")

    op.drop_index(
        "ix_scenario_security_risks_security_risk_id",
        table_name="scenario_security_risks",
    )
    op.drop_table("scenario_security_risks")
    op.drop_index(
        "ix_scenario_attack_patterns_attack_pattern_id",
        table_name="scenario_attack_patterns",
    )
    op.drop_table("scenario_attack_patterns")
    op.drop_table("scenarios")
    op.drop_table("attack_patterns")

    op.drop_index(
        "ix_security_risks_framework_version_id",
        table_name="security_risks",
    )
    op.drop_table("security_risks")
    op.drop_index(
        "ix_security_framework_versions_framework_id",
        table_name="security_framework_versions",
    )
    op.drop_table("security_framework_versions")
    op.drop_table("security_frameworks")

    bind = op.get_bind()
    duel_turn_status.drop(bind, checkfirst=True)
    duel_status.drop(bind, checkfirst=True)
    scenario_severity.drop(bind, checkfirst=True)
