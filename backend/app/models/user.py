from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.expense import Expense
    from app.models.submission import Submission


class User(TimestampMixin, Base):
    """직원 · 관리자. 사번(또는 이메일)과 비밀번호로 로그인합니다 (POST /api/auth/login)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_no: Mapped[str] = mapped_column(String(20), unique=True)  # 사번
    name: Mapped[str] = mapped_column(String(50))
    department: Mapped[str] = mapped_column(String(50))
    # 여비 직급: 직원 3급 이하 / 직원 1·2급 / 임원/본부장 …
    grade: Mapped[str] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(10), default="employee", server_default="employee")
    phone: Mapped[str | None] = mapped_column(String(20))  # 연락처
    email: Mapped[str | None] = mapped_column(String(100), unique=True)  # 로그인 아이디로도 씀
    password_hash: Mapped[str | None] = mapped_column(String(200))  # core/security.py 형식. 없으면 로그인 불가

    expenses: Mapped[list["Expense"]] = relationship(back_populates="user")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")
