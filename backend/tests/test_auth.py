"""로그인·회원가입 (POST /api/auth/*). 토큰·해시는 DB 없이, API 는 DB·시드가 있어야 하고 아니면 건너뜁니다."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError

from app.core.auth import LOGIN_REQUIRED, TOKEN_INVALID
from app.core.db import SessionLocal
from app.core.security import create_token, hash_password, read_token, verify_password
from app.domains.auth.service import LOGIN_FAILED
from app.main import app
from app.models import User

client = TestClient(app)
DEMO_PASSWORD = "nova1234"  # scripts/seed.py 의 DEMO_PASSWORD
NEW_NO = "T9999"


# ---------- DB 없이 ----------
def test_password_hash_roundtrip():
    stored = hash_password("비밀번호1234")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("비밀번호1234", stored)
    assert not verify_password("비밀번호123", stored)
    assert not verify_password("x", None)
    assert not verify_password("x", "garbage")


def test_token_roundtrip_expiry_and_tamper():
    token = create_token("E1001", now=1_000_000)
    assert read_token(token, now=1_000_000 + 60) == "E1001"
    assert read_token(token, now=1_000_000 + 8 * 86400) is None  # 7일 뒤 만료
    assert read_token(token[:-2] + "zz", now=1_000_000) is None  # 서명 훼손
    assert read_token("not.a.token", now=1_000_000) is None
    assert read_token("", now=1_000_000) is None


def test_protected_api_needs_bearer_token():
    r = client.get("/api/checklists")
    assert r.status_code == 401 and r.json()["error"] == LOGIN_REQUIRED
    r = client.get("/api/checklists", headers={"X-Employee-No": "E1001"})  # 옛 헤더는 더 이상 안 통함
    assert r.status_code == 401 and r.json()["error"] == LOGIN_REQUIRED
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401 and r.json()["error"] == TOKEN_INVALID


def test_signup_validation_without_db():
    bad = {"name": "홍길동", "employee_no": "E1", "department": "팀", "grade": "직원 3급 이하", "email": "no-at", "password": "1234"}
    r = client.post("/api/auth/signup", json=bad)
    assert r.status_code == 400 and "이메일" in r.json()["error"]
    r = client.post("/api/auth/signup", json={**bad, "email": "a@b.co", "password": "12"})
    assert r.status_code == 400 and "password" in r.json()["error"]


# ---------- DB 필요 ----------
@pytest.fixture
def db_ready():
    try:
        with SessionLocal() as db:
            seeded = db.scalar(select(User).where(User.employee_no == "E1001"))
            if seeded is None or not seeded.password_hash:
                pytest.skip("시드 전 (uv run python -m scripts.seed)")
            db.execute(delete(User).where(User.employee_no == NEW_NO))
            db.commit()
    except OperationalError:
        pytest.skip("DB 꺼짐")
    yield
    with SessionLocal() as db:
        db.execute(delete(User).where(User.employee_no == NEW_NO))
        db.commit()


def test_login_by_employee_no_and_email(db_ready):
    r = client.post("/api/auth/login", json={"login_id": "e1001", "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"] == {"employee_no": "E1001", "name": "노은비", "department": "기획팀", "grade": "직원 3급 이하", "role": "employee"}
    assert read_token(data["token"]) == "E1001"

    r = client.post("/api/auth/login", json={"login_id": "A2001@kobc.example", "password": DEMO_PASSWORD})
    assert r.status_code == 200 and r.json()["user"]["role"] == "admin"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['token']}"})
    assert me.status_code == 200 and me.json()["employee_no"] == "E1001"


def test_login_failure_does_not_reveal_which_part_is_wrong(db_ready):
    wrong_pw = client.post("/api/auth/login", json={"login_id": "E1001", "password": "nope"})
    no_user = client.post("/api/auth/login", json={"login_id": "NOSUCH", "password": DEMO_PASSWORD})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json() == {"error": LOGIN_FAILED}


def test_signup_creates_employee_only_and_rejects_duplicates(db_ready):
    body = {
        "name": "테스트직원", "employee_no": NEW_NO.lower(), "department": "해운정책팀",
        "grade": "직원 3급 이하", "email": "T9999@KOBC.example", "password": "pw1234", "role": "admin",
    }
    r = client.post("/api/auth/signup", json=body)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["user"]["role"] == "employee"  # role 을 보내도 무시
    assert data["user"]["employee_no"] == NEW_NO
    assert read_token(data["token"]) == NEW_NO

    assert client.post("/api/auth/signup", json=body).status_code == 409
    assert client.post("/api/auth/signup", json={**body, "employee_no": "T9998"}).status_code == 409  # 같은 이메일

    login = client.post("/api/auth/login", json={"login_id": "t9999@kobc.example", "password": "pw1234"})
    assert login.status_code == 200 and login.json()["user"]["name"] == "테스트직원"
