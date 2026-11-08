"""지금 사용자를 찾습니다. 시연용이라 실제 로그인·권한 검증이 아닙니다.

프론트가 X-Employee-No 헤더로 사번을 보내고, 없으면 기본 데모 직원으로 처리합니다.
헤더는 누구나 바꿔 보낼 수 있으므로 실제 서비스에는 로그인으로 교체해야 합니다.
"""

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.models import User

DEFAULT_EMPLOYEE_NO = "E1001"  # scripts/seed.py 의 데모직원1


def get_current_user(
    x_employee_no: str = Header(default=DEFAULT_EMPLOYEE_NO),
    db: Session = Depends(get_db),
) -> User:
    user = db.scalar(select(User).where(User.employee_no == x_employee_no))
    if user is None:
        raise AppError(
            f"사용자({x_employee_no})를 찾을 수 없습니다. "
            "backend 폴더에서 'uv run python -m scripts.seed' 를 실행해 주세요.",
            401,
        )
    return user
