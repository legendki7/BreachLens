"""Establish the Phase 1 migration baseline.

Revision ID: 20260814_0001
Revises:
Create Date: 2026-08-14
"""

revision: str = "20260814_0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """No domain tables are introduced in Phase 1."""


def downgrade() -> None:
    """The baseline has no schema operations to reverse."""

