from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.expense import Expense
    from app.models.submission import Submission


class User(TimestampMixin, Base):
    """직원 · 관리자. 로그인 없이 화면 상단 토글로 역할을 고르는 데모 계정."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_no: Mapped[str] = mapped_column(String(20), unique=True)  # 사번
    name: Mapped[str] = mapped_column(String(50))
    department: Mapped[str] = mapped_column(String(50))
    # 여비 직급: 직원 3급 이하 / 직원 1·2급 / 임원/본부장 …
    grade: Mapped[str] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(10), default="employee", server_default="employee")
    phone: Mapped[str | None] = mapped_column(String(20))  # 연락처

    expenses: Mapped[list["Expense"]] = relationship(back_populates="user")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")
