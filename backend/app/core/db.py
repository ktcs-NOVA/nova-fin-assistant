"""DB 연결. (Spring 의 DataSource + EntityManager 역할)

라우터에서 세션 받기 (Spring 의 @Autowired 와 비슷):

    from sqlalchemy.orm import Session
    from app.core.db import get_db

    @router.get("/api/something")
    def handler(db: Session = Depends(get_db)):
        ...
"""

from collections.abc import Iterator
from datetime import datetime

from sqlalchemy import DateTime, MetaData, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3},  # DB 가 꺼져 있으면 3초 안에 에러
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

# 제약조건 이름 규칙 — Alembic 이 변경 사항을 정확히 비교하려면 필요
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """모든 테이블(Entity)의 부모 클래스. app/models/ 에서 상속해서 씁니다."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """created_at 컬럼을 붙여주는 믹스인."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def get_db() -> Iterator[Session]:
    """요청 하나당 세션 하나. 요청이 끝나면 자동으로 닫힙니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
