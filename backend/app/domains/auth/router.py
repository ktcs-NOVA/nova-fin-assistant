from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.domains.auth import service
from app.domains.auth.schemas import AuthResponse, LoginRequest, SignupRequest, UserOut
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["로그인"])


@router.post("/signup", response_model=AuthResponse, status_code=201, summary="회원가입 (항상 직원 역할)")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    return service.auth_response(service.signup(db, req.model_dump()))


@router.post("/login", response_model=AuthResponse, summary="로그인 (사번 또는 이메일 + 비밀번호)")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    return service.auth_response(service.login(db, req.login_id, req.password))


@router.get("/me", response_model=UserOut, summary="토큰으로 내 계정 확인")
def me(user: User = Depends(get_current_user)):
    return service.to_user_out(user)
