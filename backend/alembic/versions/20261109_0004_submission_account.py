"""제출 건에 직원이 적은 계정과목 (M-05 계정과목 검토용)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("account", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("submissions", "account")
