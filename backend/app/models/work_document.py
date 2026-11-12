"""직원이 작성 중인 서류 (문서 작업): 출장보고서 · 회의록 · 출장원(정산).

쓰다 만 상태로 저장해 두고 이어서 쓸 수 있습니다.
직접 입력한 값은 fields(JSON), AI 초안 본문은 draft 입니다.
(knowledge.py 의 Document 는 규정 문서(RAG)라서 이름을 WorkDocument 로 구분했습니다.)
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class WorkDocument(TimestampMixin, Base):
    __tablename__ = "work_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # 출장보고서 | 회의록 | 출장원
    title: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(10), default="작성 중", server_default="작성 중")
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    draft: Mapped[str] = mapped_column(Text, default="", server_default="")
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
