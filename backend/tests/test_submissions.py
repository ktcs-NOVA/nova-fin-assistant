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
            trip = sub.trip
            for e in list(sub.expenses):
                db.delete(e)
            db.delete(sub)
            if trip is not None:
                db.delete(trip)
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
    assert detail["trip"] is None  # 출장 건이 아니면 출장 정보 없음

    # 방금 낸 건은 관리자 목록 맨 위에, 분 단위 제출 시각과 함께 (관리자 화면의 "새 제출" 표시용)
    newest = client.get("/api/admin/submissions", headers=auth("A2001")).json()["items"][0]
    assert newest["id"] == sub["id"]
    assert newest["submitted_time"].startswith(newest["submitted_at"] + "T") and newest["submitted_time"].endswith("+09:00")


def test_trip_submission_exposes_period(cleanup):
    """출장 건은 기간·지역을 돌려줘야 직원 화면에서 출장보고서·출장원을 이어 쓸 수 있음."""
    claim = {
        "trip_type": "국내출장", "grade": "직원 3급 이하",
        "trip": {"start_date": "2026-11-03", "end_date": "2026-11-04", "region": "광역시"},
        "items": [{"field": "일비", "amount": 60000}], "purpose": "테스트 출장",
    }
    r = client.post("/api/submissions", json=claim, headers=auth("E1001"))
    assert r.status_code == 201, r.text
    cleanup.append(r.json()["id"])
    mine = client.get("/api/submissions", headers=auth("E1001")).json()["items"]
    got = next(s for s in mine if s["id"] == r.json()["id"])
    assert got["trip"]["start_date"] == "2026-11-03" and got["trip"]["end_date"] == "2026-11-04"
    assert got["trip"]["region"] == "광역시" and got["trip"]["destination"] == "광역시"


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


def test_rejection_reasons_reach_the_employee_and_resubmission_is_linked(cleanup):
    """관리자가 고른 반려 사유가 직원에게 항목별로 보이고, 고쳐서 다시 낸 건은 원래 반려 건과 이어짐."""
    me, admin = auth("E1001"), auth("A2001")
    first = client.post("/api/submissions", json=meeting_claim(amount=620000, category="business"), headers=me).json()
    cleanup.append(first["id"])
    assert first["decision_issues"] == [] and first["resubmit_of"] is None

    picked = [
        {"field": "회의 식대", "verdict": VERDICT_FIX, "message": "사전결재가 필요합니다.", "basis": "집행 지침 제3조 제4항",
         "fix": "사전결재 서류 첨부", "rule_id": "B-PRE-APPROVAL"},
        {"field": "계정과목", "verdict": "담당자 확인 필요", "message": "계정과목이 다릅니다.", "fix": "업무추진비로 수정"},
    ]
    r = client.post(f"/api/admin/submissions/{first['id']}/decision",
                    json={"decision": "반려", "message": "사전결재 서류를 붙여 다시 내 주세요.", "issues": picked}, headers=admin)
    assert r.status_code == 200, r.text

    mine = {s["id"]: s for s in client.get("/api/submissions", headers=me).json()["items"]}
    rejected = mine[first["id"]]
    assert rejected["status"] == "반려" and rejected["decision_message"] == "사전결재 서류를 붙여 다시 내 주세요."
    # 고른 두 항목만, 직원에게 보여 줄 다섯 가지만 남음
    assert rejected["decision_issues"] == [
        {"field": "회의 식대", "verdict": VERDICT_FIX, "message": "사전결재가 필요합니다.", "basis": "집행 지침 제3조 제4항", "fix": "사전결재 서류 첨부"},
        {"field": "계정과목", "verdict": "담당자 확인 필요", "message": "계정과목이 다릅니다.", "fix": "업무추진비로 수정"},
    ]
    assert rejected["resubmitted_as"] is None

    again = meeting_claim(amount=620000, category="business", pre_approved=True)
    second = client.post("/api/submissions", json={**again, "resubmit_of": first["id"]}, headers=me)
    assert second.status_code == 201, second.text
    cleanup.append(second.json()["id"])
    assert second.json()["resubmit_of"] == first["id"]
    mine = {s["id"]: s for s in client.get("/api/submissions", headers=me).json()["items"]}
    assert mine[first["id"]]["resubmitted_as"] == second.json()["id"]
    detail = client.get(f"/api/admin/submissions/{second.json()['id']}", headers=admin).json()
    assert detail["resubmit_of"] == first["id"]

    # 남의 건이나 반려되지 않은 건으로는 "다시 제출"을 걸 수 없음
    assert client.post("/api/submissions", json={**again, "resubmit_of": first["id"]}, headers=auth("E1002")).status_code == 400
    assert client.post("/api/submissions", json={**again, "resubmit_of": second.json()["id"]}, headers=me).status_code == 400


def test_rejection_without_picked_reasons_keeps_ai_issues(cleanup):
    """사유 항목을 안 보내는 예전 화면: AI 판정의 문제 항목이 사유로 남고, 설명·수정 방법은 판정 결과에서 채움."""
    me, admin = auth("E1001"), auth("A2001")
    sub = client.post("/api/submissions", json=meeting_claim(amount=620000, category="business"), headers=me).json()
    cleanup.append(sub["id"])
    client.post(f"/api/admin/submissions/{sub['id']}/decision", json={"decision": "반려", "message": "보완 바랍니다."}, headers=admin)
    got = next(s for s in client.get("/api/submissions", headers=me).json()["items"] if s["id"] == sub["id"])
    assert got["decision_issues"] and all(i.get("message") for i in got["decision_issues"])
    assert any("사전" in i["message"] for i in got["decision_issues"])

