"""직원이 작성 중인 서류 (문서 작업): 출장보고서 · 회의록 · 출장원(정산) · 지출결과서(+검수확인서).

쓰다 만 상태로 저장해 두고 이어서 쓸 수 있습니다.
직접 입력한 값은 fields(JSON), AI 초안 본문은 draft 입니다.
정산 건에서 만든 서류는 submission_id 로 그 건에 붙고, 관리자에게 보내면 sent_at 이 찍힙니다.
(knowledge.py 의 Document 는 규정 문서(RAG)라서 이름을 WorkDocument 로 구분했습니다.)
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.submission import Submission


class WorkDocument(TimestampMixin, Base):
    __tablename__ = "work_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # 이 서류가 증빙으로 붙는 정산 건 (없으면 따로 쓴 서류)
    submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))  # 출장보고서 | 회의록 | 출장원 | 지출결과서
    title: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(10), default="작성 중", server_default="작성 중")
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    draft: Mapped[str] = mapped_column(Text, default="", server_default="")
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 관리자에게 보낸 시각
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    submission: Mapped["Submission | None"] = relationship()

    @property
    def submission_code(self) -> str | None:
        return self.submission.code if self.submission else None
