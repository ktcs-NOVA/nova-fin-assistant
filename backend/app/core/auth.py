"""지금 사용자를 찾습니다 — `Authorization: Bearer <토큰>` 헤더만 받습니다.

토큰은 POST /api/auth/login · /api/auth/signup 이 돌려주고(core/security.py), 없거나 잘못되거나 만료면 401.
예전의 X-Employee-No 헤더는 2026-11-12 PM 요청으로 없앴습니다.
"""

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import read_token
from app.models import User

LOGIN_REQUIRED = "로그인이 필요합니다."
TOKEN_INVALID = "로그인이 만료되었거나 올바르지 않습니다. 다시 로그인해 주세요."


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(LOGIN_REQUIRED, 401)
    employee_no = read_token(authorization[7:])
    if employee_no is None:
        raise AppError(TOKEN_INVALID, 401)
    user = db.scalar(select(User).where(User.employee_no == employee_no))
    if user is None:
        raise AppError(TOKEN_INVALID, 401)
    return user
