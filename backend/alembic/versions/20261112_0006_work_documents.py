"""문서 작업: 작성 중인 서류 (출장보고서·회의록·출장원)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("status", sa.String(10), server_default="작성 중", nullable=False),
        sa.Column("fields", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("draft", sa.Text(), server_default="", nullable=False),
        sa.Column("confirmed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_work_documents"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_work_documents_user_id_users", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_work_documents_user_id", "work_documents", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_work_documents_user_id", table_name="work_documents")
    op.drop_table("work_documents")
