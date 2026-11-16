"""정산 제출: 반려된 건을 고쳐 다시 낸 건이면 원래 제출 번호를 기록

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("resubmit_of", sa.String(20), nullable=True))
    op.create_index("ix_submissions_resubmit_of", "submissions", ["resubmit_of"])


def downgrade() -> None:
    op.drop_index("ix_submissions_resubmit_of", table_name="submissions")
    op.drop_column("submissions", "resubmit_of")
