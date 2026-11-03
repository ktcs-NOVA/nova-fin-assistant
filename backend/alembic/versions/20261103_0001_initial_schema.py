"""초기 테이블: 사용자 · 지출 · 정산 제출/검토 · 규정 지식베이스(pgvector) · 질의 로그

Revision ID: 0001
Revises:
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1536


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_no", sa.String(20), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("department", sa.String(50), nullable=False),
        sa.Column("grade", sa.String(20), nullable=False),
        sa.Column("role", sa.String(10), server_default="employee", nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("employee_no", name="uq_users_employee_no"),
    )

    op.create_table(
        "trips",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("destination", sa.String(100), nullable=True),
        sa.Column("region", sa.String(10), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("vehicle", sa.String(20), nullable=True),
        sa.Column("private_car_approved", sa.Boolean(), server_default="false", nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_trips"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_trips_user_id_users"),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("purpose", sa.String(200), nullable=False),
        sa.Column("total_amount", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(10), server_default="검토 대기", nullable=False),
        sa.Column("step", sa.Integer(), nullable=True),
        sa.Column("verdict", sa.String(20), nullable=True),
        sa.Column("verify_result", postgresql.JSONB(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_submissions"),
        sa.UniqueConstraint("code", name="uq_submissions_code"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_submissions_user_id_users"),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["trips.id"], name="fk_submissions_trip_id_trips", ondelete="SET NULL"
        ),
    )

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=True),
        sa.Column("submission_id", sa.Integer(), nullable=True),
        sa.Column("field", sa.String(30), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("used_date", sa.Date(), nullable=False),
        sa.Column("used_time", sa.Time(), nullable=True),
        sa.Column("payment", sa.String(20), server_default="법인카드", nullable=False),
        sa.Column("merchant", sa.String(100), nullable=True),
        sa.Column("merchant_type", sa.String(50), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("attendees", postgresql.JSONB(), nullable=True),
        sa.Column("extra", postgresql.JSONB(), server_default="{}", nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_expenses"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_expenses_user_id_users"),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["trips.id"], name="fk_expenses_trip_id_trips", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions.id"],
            name="fk_expenses_submission_id_submissions",
            ondelete="SET NULL",
        ),
    )

    op.create_table(
        "receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expense_id", sa.Integer(), nullable=True),
        sa.Column("image_path", sa.String(255), nullable=True),
        sa.Column("ocr_result", postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.String(10), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_receipts"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_receipts_user_id_users"),
        sa.ForeignKeyConstraint(
            ["expense_id"],
            ["expenses.id"],
            name="fk_receipts_expense_id_expenses",
            ondelete="SET NULL",
        ),
    )

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("decision", sa.String(10), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("sources", postgresql.JSONB(), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_reviews"),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["submissions.id"],
            name="fk_reviews_submission_id_submissions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name="fk_reviews_reviewer_id_users", ondelete="SET NULL"
        ),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("doc_type", sa.String(20), server_default="규정", nullable=False),
        sa.Column("audience", sa.String(10), server_default="all", nullable=False),
        sa.Column("source_file", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("revised_at", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("chunk_type", sa.String(20), server_default="article", nullable=False),
        sa.Column("article", sa.String(30), nullable=True),
        sa.Column("article_title", sa.String(100), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("revised_at", sa.Date(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_chunks_document_id_documents",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "query_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("feature", sa.String(30), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("grounded", sa.Boolean(), nullable=True),
        sa.Column("sources", postgresql.JSONB(), nullable=True),
        sa.Column("retrieved", postgresql.JSONB(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_query_logs"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_query_logs_user_id_users", ondelete="SET NULL"
        ),
    )


def downgrade() -> None:
    op.drop_table("query_logs")
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("reviews")
    op.drop_table("receipts")
    op.drop_table("expenses")
    op.drop_table("submissions")
    op.drop_table("trips")
    op.drop_table("users")
