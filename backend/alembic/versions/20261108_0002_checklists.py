"""직원별 업무 체크리스트 (U-02)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "checklists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("task", sa.String(100), nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("deadline", postgresql.JSONB(), nullable=True),
        sa.Column("approver", postgresql.JSONB(), nullable=True),
        sa.Column("sources", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_checklists"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_checklists_user_id_users", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_checklists_user_id", "checklists", ["user_id"])
    op.create_table(
        "checklist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("checklist_id", sa.Integer(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text(), server_default="", nullable=False),
        sa.Column("basis", sa.Text(), server_default="", nullable=False),
        sa.Column("done", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_checklist_items"),
        sa.ForeignKeyConstraint(
            ["checklist_id"],
            ["checklists.id"],
            name="fk_checklist_items_checklist_id_checklists",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_checklist_items_checklist_id", "checklist_items", ["checklist_id"])


def downgrade() -> None:
    op.drop_index("ix_checklist_items_checklist_id", table_name="checklist_items")
    op.drop_table("checklist_items")
    op.drop_index("ix_checklists_user_id", table_name="checklists")
    op.drop_table("checklists")
