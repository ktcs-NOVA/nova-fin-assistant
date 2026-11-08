"""직원이 저장한 업무 체크리스트 (U-02).

저장할 때의 절차 안내를 그대로 복사해 둡니다. 규정이 개정되어도 저장한 내용은 바뀌지 않으므로,
sources 에 남긴 개정일로 어느 시점 기준인지 알 수 있습니다.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class Checklist(TimestampMixin, Base):
    __tablename__ = "checklists"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    task: Mapped[str] = mapped_column(String(100))  # 국내 출장비 정산
    summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    deadline: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # { text, basis, check }
    approver: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # { text, basis, check }
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")

    items: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="checklist", cascade="all, delete-orphan", order_by="ChecklistItem.seq"
    )


class ChecklistItem(Base):
    """체크 항목 하나. kind 는 document(필요 서류) 또는 step(작성 순서)입니다."""

    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    checklist_id: Mapped[int] = mapped_column(
        ForeignKey("checklists.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(Text, default="", server_default="")
    basis: Mapped[str] = mapped_column(Text, default="", server_default="")
    done: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    checklist: Mapped["Checklist"] = relationship(back_populates="items")
