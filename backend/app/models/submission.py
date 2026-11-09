"""정산 제출(Submission)과 관리자 검토 기록(Review) — M-01 검토 대기함.

필드는 프론트 관리자 화면 목업(frontend/src/mocks/submissions.json)에 맞췄습니다.
상태 값은 app/core/constants.py 의 STATUS_* ("검토 대기" / "승인" / "반려").
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.expense import Expense, Trip
    from app.models.user import User


class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)  # 화면에 보이는 번호: S-2026-001
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("trips.id", ondelete="SET NULL"))

    type: Mapped[str] = mapped_column(String(20))  # 국내출장 / 법인카드 / 업무추진비
    purpose: Mapped[str] = mapped_column(String(200))
    total_amount: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    account: Mapped[str | None] = mapped_column(String(30))  # 직원이 결의서에 적은 계정과목 (M-05 비교용)

    status: Mapped[str] = mapped_column(String(10), default="검토 대기", server_default="검토 대기")
    step: Mapped[int | None] = mapped_column(Integer)  # 상단 처리 단계 표시용
    # AI 사전검증 결과 (U-04 엔진 응답을 그대로 저장)
    verdict: Mapped[str | None] = mapped_column(String(20))  # overall
    verify_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="submissions")
    trip: Mapped["Trip | None"] = relationship()  # 출장 제출이면 출장 정보 (기간·지역)
    expenses: Mapped[list["Expense"]] = relationship(back_populates="submission")
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class Review(TimestampMixin, Base):
    """관리자의 승인/반려 기록. 승인은 항상 사람이 누른다."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"))
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decision: Mapped[str] = mapped_column(String(10))  # 승인 / 반려
    message: Mapped[str | None] = mapped_column(Text)  # 반려 사유 (U-09 해석 대상)
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)  # 반려 근거 조항

    submission: Mapped["Submission"] = relationship(back_populates="reviews")
