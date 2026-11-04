"""질의 로그 — 정확도 평가(최종보고서)와 M-08 문의 현황 분석에 씁니다."""

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class QueryLog(TimestampMixin, Base):
    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    feature: Mapped[str] = mapped_column(String(30))  # qa / procedure / reject-draft …
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text)
    grounded: Mapped[bool | None] = mapped_column()  # 근거를 찾았는지 (False = 근거 없음 질문)
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    retrieved: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)  # 조각 id · 점수
    latency_ms: Mapped[int | None] = mapped_column(Integer)
