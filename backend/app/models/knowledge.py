"""RAG 지식베이스: 규정 문서(Document)와 조항 조각(Chunk) + 임베딩 벡터(pgvector).

임베딩 차원(1536)은 OpenAI text-embedding-3-small 기준입니다.
임베딩 모델을 바꾸면 이 숫자 + 마이그레이션을 함께 바꾸고 문서를 다시 적재해야 합니다.
"""

from datetime import date
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin

EMBEDDING_DIM = 1536


class Document(TimestampMixin, Base):
    """규정 문서 1개 (예: 여비규정 2026.10.21 개정본)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))  # 규정명 — 출처 표시에 그대로 쓰임
    doc_type: Mapped[str] = mapped_column(String(20), default="규정", server_default="규정")
    audience: Mapped[str] = mapped_column(String(10), default="all", server_default="all")
    source_file: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(500))  # 원문 링크 (U-03)
    revised_at: Mapped[date | None] = mapped_column(Date)  # 최종 개정일
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    content_hash: Mapped[str] = mapped_column(String(64))  # 바뀐 문서만 다시 적재하기 위함

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Chunk.seq"
    )


class Chunk(TimestampMixin, Base):
    """검색 단위 조각. 기본은 조(條) 하나 = 조각 하나."""

    __tablename__ = "chunks"
    __table_args__ = (
        # 코사인 거리 기반 벡터 인덱스 (HNSW)
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer)  # 문서 안 순서
    chunk_type: Mapped[str] = mapped_column(String(20), default="article", server_default="article")
    article: Mapped[str | None] = mapped_column(String(30))  # 제14조, 제3조의2, 별표 1 …
    article_title: Mapped[str | None] = mapped_column(String(100))  # 일비, 식비, 숙박비
    content: Mapped[str] = mapped_column(Text)
    revised_at: Mapped[date | None] = mapped_column(Date)  # 조항별 최근 개정일
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    document: Mapped["Document"] = relationship(back_populates="chunks")
