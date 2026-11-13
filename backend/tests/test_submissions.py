"""정산 제출 API — 회의비 건의 참석자·회의 목적이 저장되어 관리자 화면까지 가는지. DB·시드가 있어야 하고 아니면 건너뜁니다."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.constants import VERDICT_FIX
from app.core.db import SessionLocal
from app.core.security import create_token
from app.domains.submissions.service import _as_list
from app.main import app
from app.models import Submission, User

client = TestClient(app)


def auth(employee_no: str) -> dict:
    return {"Authorization": f"Bearer {create_token(employee_no)}"}


def test_attendees_are_stored_as_list():
    assert _as_list(None) is None and _as_list([]) is None and _as_list("") is None
    assert _as_list("홍길동 외 3명") == ["홍길동 외 3명"]
    assert _as_list(["홍길동", " ", "김철수"]) == ["홍길동", "김철수"]


@pytest.fixture
def cleanup():
    try:
        with SessionLocal() as db:
            if db.scalar(select(User).where(User.employee_no == "E1001")) is None:
                pytest.skip("시드 전")
    except OperationalError:
        pytest.skip("DB 꺼짐")
    codes = []
    yield codes
    with SessionLocal() as db:
        for sub in db.scalars(select(Submission).where(Submission.code.in_(codes))):
            for e in list(sub.expenses):
                db.delete(e)
            db.delete(sub)
        db.commit()


def meeting_claim(**item):
    base = {
        "field": "회의 식대", "amount": 120000, "date": "2026-11-10", "time": "12:30", "payment": "법인카드",
        "merchant": "테스트식당", "category": "org", "meeting_purpose": "테스트 업무협의",
        "attendees": ["기획팀 노은비", "해운정책팀 황종원"], "participant_count": 2,
    }
    return {"trip_type": "회의비", "grade": "직원 3급 이하", "settlement_date": "2026-11-12",
            "items": [{**base, **item}], "purpose": "테스트 업무협의", "account": "조직관리비"}


def test_meeting_submission_keeps_purpose_and_attendees(cleanup):
    r = client.post("/api/submissions", json=meeting_claim(), headers=auth("E1001"))
    assert r.status_code == 201, r.text
    sub = r.json()
    cleanup.append(sub["id"])
    assert sub["type"] == "회의비" and sub["purpose"] == "테스트 업무협의"

    detail = client.get(f"/api/admin/submissions/{sub['id']}", headers=auth("A2001")).json()
    first = detail["expenses"][0]
    assert first["attendees"] == ["기획팀 노은비", "해운정책팀 황종원"]
    assert first["meeting_purpose"] == "테스트 업무협의" and first["participant_count"] == 2


def test_external_meeting_over_500k_needs_pre_approval(cleanup):
    """외부 참석 회의(category business)는 업무추진비 기준: 건당 50만 원 이상이면 사전결재."""
    claim = meeting_claim(amount=620000, category="business")
    r = client.post("/api/submissions", json=claim, headers=auth("E1001"))
    assert r.status_code == 201, r.text
    cleanup.append(r.json()["id"])
    assert r.json()["verdict"] == VERDICT_FIX
    assert any(i.get("rule_id") == "B-PRE-APPROVAL" for i in r.json()["items"])

    ok = meeting_claim(amount=620000, category="business", pre_approved=True)
    r = client.post("/api/submissions", json=ok, headers=auth("E1001"))
    cleanup.append(r.json()["id"])
    assert not any(i.get("rule_id") == "B-PRE-APPROVAL" for i in r.json()["items"])

    internal = meeting_claim(amount=620000)  # 내부 회의는 50만 원 기준을 적용하지 않음
    r = client.post("/api/submissions", json=internal, headers=auth("E1001"))
    cleanup.append(r.json()["id"])
    assert not any(i.get("rule_id") == "B-PRE-APPROVAL" for i in r.json()["items"])
