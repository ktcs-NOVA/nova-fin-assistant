"""문서 작업: 서류를 정산 건에 붙이고 관리자에게 보낸 시각을 기록

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("work_documents", sa.Column("submission_id", sa.Integer(), nullable=True))
    op.add_column("work_documents", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_work_documents_submission_id_submissions",
        "work_documents",
        "submissions",
        ["submission_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_work_documents_submission_id", "work_documents", ["submission_id"])


def downgrade() -> None:
    op.drop_index("ix_work_documents_submission_id", table_name="work_documents")
    op.drop_constraint(
        "fk_work_documents_submission_id_submissions", "work_documents", type_="foreignkey"
    )
    op.drop_column("work_documents", "sent_at")
    op.drop_column("work_documents", "submission_id")
