"""지출 데이터: 출장 묶음(Trip) · 지출 건(Expense) · 영수증(Receipt)

필드 이름은 U-04 검증 엔진(backend/app/precheck)의 입력과 맞췄습니다.
엔진이 쓰는 선택 필드(nights, breakfast_included, reason_doc …)는 컬럼으로 다 만들지 않고
`extra`(JSONB)에 넣어 둡니다. 자주 쓰게 되면 그때 컬럼으로 올리세요.
"""

from datetime import date, time
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.submission import Submission
    from app.models.user import User


class Trip(TimestampMixin, Base):
    """출장 한 건 (여러 지출 건을 묶는 단위 — 출장 묶음 검증용)."""

    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(10))  # 서울 / 광역시 / 기타
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    # 대중교통 / 업무용차량 / 렌트차량 / 자가용
    vehicle: Mapped[str | None] = mapped_column(String(20))
    private_car_approved: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    user: Mapped["User"] = relationship()
    expenses: Mapped[list["Expense"]] = relationship(back_populates="trip")


class Expense(TimestampMixin, Base):
    """지출 건 하나 (카드 결제 1건, 영수증 1장 단위)."""

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    trip_id: Mapped[int | None] = mapped_column(ForeignKey("trips.id", ondelete="SET NULL"))
    submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="SET NULL")
    )

    field: Mapped[str] = mapped_column(String(30))  # 항목: 식비 / 숙박비 / 교통비 / 회의비 …
    amount: Mapped[int] = mapped_column(Integer)
    used_date: Mapped[date] = mapped_column(Date)
    used_time: Mapped[time | None] = mapped_column(Time)  # 심야·주말 검사용
    payment: Mapped[str] = mapped_column(String(20), default="법인카드", server_default="법인카드")
    merchant: Mapped[str | None] = mapped_column(String(100))
    merchant_type: Mapped[str | None] = mapped_column(String(50))  # 업종 (금지 업종 검사용)
    note: Mapped[str | None] = mapped_column(Text)
    attendees: Mapped[list[str] | None] = mapped_column(JSONB)  # 참석자 명단
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")

    user: Mapped["User"] = relationship(back_populates="expenses")
    trip: Mapped["Trip | None"] = relationship(back_populates="expenses")
    submission: Mapped["Submission | None"] = relationship(back_populates="expenses")
    receipts: Mapped[list["Receipt"]] = relationship(back_populates="expense")


class Receipt(TimestampMixin, Base):
    """영수증 사진과 인식 결과 (U-06)."""

    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expense_id: Mapped[int | None] = mapped_column(ForeignKey("expenses.id", ondelete="SET NULL"))
    image_path: Mapped[str | None] = mapped_column(String(255))
    ocr_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # 가맹점·금액·일시 등 추출값
    confidence: Mapped[str | None] = mapped_column(String(10))  # high / medium / low

    expense: Mapped["Expense | None"] = relationship(back_populates="receipts")
