"""회원가입·로그인. 가입은 항상 직원 역할이고 관리자는 시드(scripts/seed.py)로만 만듭니다."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import ROLE_EMPLOYEE
from app.core.errors import AppError
from app.core.security import create_token, hash_password, verify_password
from app.models import User

LOGIN_FAILED = "사번(또는 이메일)이나 비밀번호가 맞지 않습니다."


def to_user_out(user: User) -> dict:
    return {
        "employee_no": user.employee_no,
        "name": user.name,
        "department": user.department,
        "grade": user.grade,
        "role": user.role,
    }


def auth_response(user: User) -> dict:
    return {"token": create_token(user.employee_no), "user": to_user_out(user)}


def signup(db: Session, data: dict) -> User:
    employee_no = data["employee_no"].strip().upper()
    email = data["email"].strip().lower()
    if db.scalar(select(User).where(User.employee_no == employee_no)):
        raise AppError(f"이미 가입된 사번입니다: {employee_no}", 409)
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise AppError("이미 가입된 이메일입니다.", 409)
    user = User(
        employee_no=employee_no,
        name=data["name"].strip(),
        department=data["department"].strip(),
        grade=data["grade"].strip(),
        role=ROLE_EMPLOYEE,  # 가입으로는 관리자를 만들 수 없음
        email=email,
        password_hash=hash_password(data["password"]),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, login_id: str, password: str) -> User:
    key = login_id.strip()
    user = db.scalar(
        select(User).where((User.employee_no == key.upper()) | (func.lower(User.email) == key.lower()))
    )
    # 사번이 없는 경우와 비밀번호가 틀린 경우를 구분하지 않음 (계정 존재 여부 노출 방지)
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(LOGIN_FAILED, 401)
    return user
