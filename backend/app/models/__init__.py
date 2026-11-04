"""DB 테이블 정의 (Spring 의 @Entity 모음).

새 테이블을 만들면 반드시 여기에 import 를 추가하세요.
Alembic 이 이 목록을 보고 변경 사항(마이그레이션)을 자동으로 만듭니다.

    uv run alembic revision --autogenerate -m "설명"
    uv run alembic upgrade head
"""

from app.models.expense import Expense, Receipt, Trip
from app.models.knowledge import Chunk, Document
from app.models.log import QueryLog
from app.models.submission import Review, Submission
from app.models.user import User

__all__ = [
    "Chunk",
    "Document",
    "Expense",
    "QueryLog",
    "Receipt",
    "Review",
    "Submission",
    "Trip",
    "User",
]
