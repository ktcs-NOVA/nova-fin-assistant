"""로그인·회원가입 요청/응답 모양 (docs/API.md 3-10)."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserOut(BaseModel):
    employee_no: str
    name: str
    department: str
    grade: str
    role: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class SignupRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "홍길동",
                    "employee_no": "E1010",
                    "department": "해운정책팀",
                    "grade": "직원 3급 이하",
                    "email": "hong@kobc.example",
                    "password": "nova1234",
                }
            ]
        }
    )

    name: str = Field(min_length=1, max_length=50)
    employee_no: str = Field(min_length=1, max_length=20, description="사번. 로그인 아이디로 씁니다")
    department: str = Field(min_length=1, max_length=50)
    grade: str = Field(min_length=1, max_length=20, description="여비 직급 (직원 3급 이하 / 직원 1·2급 / 임원/본부장 / 감사 / 사장)")
    email: str = Field(max_length=100)
    password: str = Field(min_length=4, max_length=100)

    @field_validator("email")
    @classmethod
    def _email_shape(cls, v: str) -> str:
        v = v.strip()
        if not _EMAIL.match(v):
            raise ValueError("이메일 형식이 올바르지 않습니다.")
        return v


class LoginRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"login_id": "E1001", "password": "nova1234"}]})

    login_id: str = Field(min_length=1, description="사번 또는 이메일")
    password: str = Field(min_length=1)
