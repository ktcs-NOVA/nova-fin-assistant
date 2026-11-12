"""시연·개발용 가상 데이터를 넣습니다. 여러 번 실행해도 중복으로 들어가지 않습니다.

    uv run python -m scripts.seed

모든 이름·금액은 가상입니다. 데이터를 바꾸고 싶으면 이 파일을 고친 뒤
'docker compose down -v → docker compose up -d → alembic upgrade head → seed' 순서로 초기화하세요.
"""

import sys
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.constants import (
    CONTACT_EMPLOYEE_NO,
    ROLE_ADMIN,
    ROLE_EMPLOYEE,
    STATUS_PENDING,
)
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import Expense, Submission, Trip, User

KST = ZoneInfo("Asia/Seoul")

USERS = [
    # 사번, 이름, 부서, 여비 직급, 역할
    ("E1001", "노은비", "기획팀", "직원 3급 이하", ROLE_EMPLOYEE),
    ("E1002", "박철환", "총무인사부", "직원 1·2급", ROLE_EMPLOYEE),
    ("E1003", "황종원", "해운정책팀", "직원 3급 이하", ROLE_EMPLOYEE),
    ("A2001", "이채은", "재무회계부", "직원 1·2급", ROLE_ADMIN),
    (CONTACT_EMPLOYEE_NO, "이채은사원", "재무회계부", "직원 1·2급", ROLE_ADMIN),
]

# 연락처도 가상입니다. 실제 담당자가 정해지면 이 값과 위 계정을 바꾸세요.
PHONES = {CONTACT_EMPLOYEE_NO: "000-0000-0000"}

# 시연 계정 공통 비밀번호 · 이메일 (로그인 화면 안내문과 같아야 함). 가상 도메인입니다.
DEMO_PASSWORD = "nova1234"
EMAIL_DOMAIN = "kobc.example"


def seed_users(db) -> dict[str, User]:
    users = {}
    for no, name, dept, grade, role in USERS:
        user = db.scalar(select(User).where(User.employee_no == no))
        if user is None:
            user = User(
                employee_no=no,
                name=name,
                department=dept,
                grade=grade,
                role=role,
                phone=PHONES.get(no),
            )
            db.add(user)
        else:
            # 옛 시드(예: '데모직원1')로 만들어진 시연 계정의 이름·부서·직급·역할을 이 목록과 맞춤
            user.name, user.department, user.grade, user.role = name, dept, grade, role
        # 로그인 정보가 없는 계정(옛 시드 포함)에 이메일·비밀번호를 채움. 팀원은 시드를 다시 실행해야 로그인됨
        if not user.email:
            user.email = f"{no.lower()}@{EMAIL_DOMAIN}"
        if not user.password_hash:
            user.password_hash = hash_password(DEMO_PASSWORD)
        users[no] = user
    db.flush()
    return users


def seed_sample_submission(db, users: dict[str, User]) -> None:
    """검토 대기함(M-01)에 보일 예시 제출 건 1개: 부산 1박 2일 출장."""
    if db.scalar(select(Submission).where(Submission.code == "S-2026-001")):
        return

    user = users["E1001"]
    trip = Trip(
        user=user,
        title="부산 해운물류 간담회 출장",
        destination="부산",
        region="광역시",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 21),
        vehicle="대중교통",
    )
    expenses = [
        Expense(
            user=user,
            trip=trip,
            field="교통비",
            amount=59800,
            used_date=date(2026, 10, 20),
            used_time=time(8, 10),
            payment="법인카드",
            merchant="한국철도공사",
            merchant_type="철도",
        ),
        Expense(
            user=user,
            trip=trip,
            field="숙박비",
            amount=88000,
            used_date=date(2026, 10, 20),
            used_time=time(21, 5),
            payment="법인카드",
            merchant="부산 OO호텔",
            merchant_type="숙박",
            extra={"nights": 1, "breakfast_included": True, "receipt": True},
        ),
        Expense(
            user=user,
            trip=trip,
            field="식비",
            amount=30000,
            used_date=date(2026, 10, 21),
            used_time=time(12, 30),
            payment="법인카드",
            merchant="OO식당",
            merchant_type="한식",
        ),
    ]
    submission = Submission(
        code="S-2026-001",
        user=user,
        type="국내출장",
        purpose=trip.title,
        total_amount=sum(e.amount for e in expenses),
        status=STATUS_PENDING,
        step=2,
        submitted_at=datetime(2026, 10, 22, 9, 0, tzinfo=KST),
    )
    for e in expenses:
        e.submission = submission
    db.add_all([trip, submission, *expenses])
    db.flush()
    submission.trip_id = trip.id


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    with SessionLocal() as db:
        users = seed_users(db)
        seed_sample_submission(db, users)
        db.commit()
        print(f"사용자 {len(users)}명, 예시 제출 건 S-2026-001 준비 완료")


if __name__ == "__main__":
    main()
