"""출장 신청: 출발·복귀 시각과 동행 출장자 (여비규정 별지 제1호 출장원의 '일시' · '출장자' 칸)

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trips", sa.Column("start_time", sa.Time(), nullable=True))
    op.add_column("trips", sa.Column("end_time", sa.Time(), nullable=True))
    op.add_column("trips", sa.Column("companions", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("trips", "companions")
    op.drop_column("trips", "end_time")
    op.drop_column("trips", "start_time")
