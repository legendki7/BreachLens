"""Add Phase 8 Duel turn evidence persistence.

Revision ID: 20260825_0003
Revises: 20260816_0002
Create Date: 2026-08-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260825_0003"
down_revision: str | None = "20260816_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
    op.add_column("duel_turns", sa.Column("failure_stage", sa.String(80), nullable=True))
    op.add_column("duel_turns", sa.Column("failure_category", sa.String(120), nullable=True))
    op.add_column("duel_turns", sa.Column("failure_message", sa.String(500), nullable=True))
    op.add_column(
        "duel_turns", sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table(
        "duel_turn_attacks",
        sa.Column("duel_turn_id", sa.Uuid(), nullable=False),
        sa.Column("attack_pattern_id", sa.Uuid(), nullable=False),
        sa.Column("attack_prompt", sa.Text(), nullable=False),
        sa.Column("effective_prompt", sa.Text(), nullable=True),
        sa.Column("strategy_summary", sa.Text(), nullable=False),
        sa.Column("adaptation_reason", sa.Text(), nullable=False),
        sa.Column("attacker_model_id", sa.String(512), nullable=False),
        sa.Column("attacker_provider", sa.String(80), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["attack_pattern_id"], ["attack_patterns.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["duel_turn_id"], ["duel_turns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("duel_turn_id"),
    )
    op.create_index(
        "ix_duel_turn_attacks_attack_pattern_id",
        "duel_turn_attacks",
        ["attack_pattern_id"],
    )

    op.create_table(
        "duel_turn_model_executions",
        sa.Column("duel_turn_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.String(512), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("raw_response", sa.Text(), nullable=False),
        sa.Column("system_visible_response", sa.Text(), nullable=True),
        sa.Column("finish_reason", sa.String(120), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["duel_turn_id"], ["duel_turns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("duel_turn_id"),
    )

    op.create_table(
        "duel_turn_guardrail_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("duel_turn_id", sa.Uuid(), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("final_decision", sa.String(20), nullable=False),
        sa.Column("original_content", sa.Text(), nullable=False),
        sa.Column("final_content", sa.Text(), nullable=True),
        sa.Column("total_latency_ms", sa.Float(), nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["duel_turn_id"], ["duel_turns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "duel_turn_id",
            "stage",
            name="uq_duel_turn_guardrail_reports_turn_stage",
        ),
    )
    op.create_index(
        "ix_duel_turn_guardrail_reports_duel_turn_id",
        "duel_turn_guardrail_reports",
        ["duel_turn_id"],
    )
    op.create_index(
        "ix_duel_turn_guardrail_reports_final_decision",
        "duel_turn_guardrail_reports",
        ["final_decision"],
    )

    op.create_table(
        "duel_turn_evaluations",
        sa.Column("duel_turn_id", sa.Uuid(), nullable=False),
        sa.Column("model_outcome", sa.String(40), nullable=True),
        sa.Column("model_attack_success_score", sa.Float(), nullable=True),
        sa.Column("system_outcome", sa.String(40), nullable=False),
        sa.Column("system_attack_success_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("rubric_id", sa.String(255), nullable=False),
        sa.Column("rubric_version", sa.String(80), nullable=False),
        sa.Column("judge_reason", sa.Text(), nullable=True),
        sa.Column("judge_model_id", sa.String(512), nullable=True),
        sa.Column("judge_provider", sa.String(80), nullable=True),
        sa.Column("evaluation_latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["duel_turn_id"], ["duel_turns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("duel_turn_id"),
    )
    op.create_index(
        "ix_duel_turn_evaluations_model_outcome",
        "duel_turn_evaluations",
        ["model_outcome"],
    )
    op.create_index(
        "ix_duel_turn_evaluations_system_outcome",
        "duel_turn_evaluations",
        ["system_outcome"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_duel_turn_evaluations_system_outcome",
        table_name="duel_turn_evaluations",
    )
    op.drop_index(
        "ix_duel_turn_evaluations_model_outcome",
        table_name="duel_turn_evaluations",
    )
    op.drop_table("duel_turn_evaluations")
    op.drop_index(
        "ix_duel_turn_guardrail_reports_final_decision",
        table_name="duel_turn_guardrail_reports",
    )
    op.drop_index(
        "ix_duel_turn_guardrail_reports_duel_turn_id",
        table_name="duel_turn_guardrail_reports",
    )
    op.drop_table("duel_turn_guardrail_reports")
    op.drop_table("duel_turn_model_executions")
    op.drop_index(
        "ix_duel_turn_attacks_attack_pattern_id",
        table_name="duel_turn_attacks",
    )
    op.drop_table("duel_turn_attacks")
    op.drop_column("duel_turns", "failed_at")
    op.drop_column("duel_turns", "failure_message")
    op.drop_column("duel_turns", "failure_category")
    op.drop_column("duel_turns", "failure_stage")
