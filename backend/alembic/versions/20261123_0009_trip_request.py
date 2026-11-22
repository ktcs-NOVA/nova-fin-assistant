"""출장 신청: 출장을 정산 전에 미리 등록 (구분 · 상태 · 편도 거리 · 교육 여부 · 출장 시간)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trips", sa.Column("trip_type", sa.String(20), nullable=True))
    op.add_column("trips", sa.Column("status", sa.String(10), nullable=True))
    op.add_column("trips", sa.Column("distance_km", sa.Float(), nullable=True))
    op.add_column(
        "trips",
        sa.Column("education", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("trips", sa.Column("hours", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("trips", "hours")
    op.drop_column("trips", "education")
    op.drop_column("trips", "distance_km")
    op.drop_column("trips", "status")
    op.drop_column("trips", "trip_type")
