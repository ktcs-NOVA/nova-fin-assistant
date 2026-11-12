"""문서 작업(출장보고서·회의록·출장원) 테스트.

앞부분은 DB 없이 도는 초안 계산 테스트, 뒷부분은 API 테스트(DB·시드가 없으면 건너뜀).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.db import SessionLocal
from app.core.security import create_token
from app.domains.documents import drafts
from app.main import app
from app.models import User


def auth(employee_no: str) -> dict:
    return {"Authorization": f"Bearer {create_token(employee_no)}"}


TRIP = {
    "trip_start": "2026-11-03",
    "trip_end": "2026-11-05",
    "destination": "부산 영도",
    "purpose": "부산지사 현장 점검",
    "work_notes": "지사 설비 점검 및 담당자 면담",
    "transport_fee": 59800,
    "lodging_fee": 160000,
}
MEETING = {
    "meeting_title": "주간 업무 회의",
    "meeting_date": "2026-11-10",
    "attendees": ["노은비", "김철환", "이수정"],
    "receipt_amount": 100000,
    "notes": "다음 주 일정 논의",
}


# ── 초안 계산 (DB 불필요) ──
def test_period_counts_nights():
    assert drafts.period("2026-11-03", "2026-11-05").endswith("(2박 3일)")
    assert drafts.period("2026-11-03", "2026-11-03").endswith("(당일)")


def test_per_person_rounds_half_up():
    assert drafts.per_person(100000, 3) == 33333
    assert drafts.per_person(100001, 2) == 50001  # 50000.5 → 반올림
    assert drafts.per_person(1000, 0) == 0


def test_missing_lists_empty_required_fields():
    assert drafts.missing("출장보고서", {}) == list(drafts.REQUIRED["출장보고서"].values())
    assert drafts.missing("출장보고서", TRIP) == []
    assert drafts.missing("회의록", {**MEETING, "attendees": []}) == ["참석자"]
    assert drafts.missing("출장원", {**TRIP, "total_amount": "0"}) == ["정산 금액"]


def test_trip_report_totals_come_from_inputs():
    text = drafts.build("출장보고서", TRIP, "노은비 (재무팀)")
    assert "출장 기간: 2026년 11월 3일 ~ 2026년 11월 5일 (2박 3일)" in text
    assert "교통비: 59,800원" in text and "숙박비: 160,000원" in text
    assert "합계: 219,800원" in text
    assert "식비" not in text  # 입력 안 한 항목은 만들어 넣지 않음


def test_meeting_minutes_per_person_amount():
    text = drafts.build("회의록", MEETING, "노은비 (재무팀)")
    assert "참석자: 3명 (노은비, 김철환, 이수정)" in text
    assert "1인당 33,333원" in text


def test_polish_only_touches_free_text():
    text = drafts.build("출장보고서", TRIP, "노은비 (재무팀)", polish=lambda t: f"[다듬음]{t}")
    assert "[다듬음]지사 설비 점검 및 담당자 면담" in text
    assert text.count("[다듬음]") == 1
    assert "합계: 219,800원" in text


def test_travel_order_defaults_signature_blank():
    text = drafts.build("출장원", {**TRIP, "total_amount": 219800}, "노은비 (재무팀)")
    assert "정산 금액: 219,800원" in text and "(서명 전)" in text


# ── API (DB 필요) ──
client = TestClient(app, headers=auth("E1001"))
OTHER = auth("E1002")


@pytest.fixture
def doc():
    try:
        with SessionLocal() as db:
            ready = db.scalar(select(User).where(User.employee_no == "E1002")) and db.scalar(
                select(User).where(User.employee_no == "E1001")
            )
    except OperationalError:
        pytest.skip("DB 꺼짐")
    if not ready:
        pytest.skip("시드 전")
    r = client.post("/api/documents", json={"kind": "출장보고서", "fields": TRIP})
    assert r.status_code == 201, r.text
    data = r.json()
    yield data
    client.delete(f"/api/documents/{data['id']}")


def test_create_sets_default_title_and_working_status(doc):
    assert doc["title"] == "출장보고서 · 부산 영도"
    assert doc["status"] == "작성 중" and doc["confirmed"] is False and doc["draft"] == ""


def test_list_returns_only_mine(doc):
    mine = client.get("/api/documents").json()
    assert doc["id"] in [d["id"] for d in mine]
    assert client.get("/api/documents", headers=OTHER).json() == [] or doc["id"] not in [
        d["id"] for d in client.get("/api/documents", headers=OTHER).json()
    ]


def test_other_users_document_is_404(doc):
    url = f"/api/documents/{doc['id']}"
    assert client.get(url, headers=OTHER).status_code == 404
    assert client.patch(url, json={"title": "x"}, headers=OTHER).status_code == 404
    assert client.delete(url, headers=OTHER).status_code == 404
    assert client.post(url + "/draft", headers=OTHER).status_code == 404


def test_draft_needs_required_fields():
    try:
        r = client.post(
            "/api/documents", json={"kind": "회의록", "fields": {"meeting_title": "회의"}}
        )
    except OperationalError:
        pytest.skip("DB 꺼짐")
    if r.status_code != 201:
        pytest.skip("DB 준비 전")
    d = r.json()
    try:
        r2 = client.post(f"/api/documents/{d['id']}/draft")
        assert r2.status_code == 400
        assert (
            "참석자" in r2.json()["message"]
            if "message" in r2.json()
            else "참석자" in str(r2.json())
        )
    finally:
        client.delete(f"/api/documents/{d['id']}")


def test_draft_then_confirm_then_edit_resets_confirmation(doc):
    url = f"/api/documents/{doc['id']}"
    # 초안 전에는 확인 완료 불가
    assert client.patch(url, json={"confirmed": True}).status_code == 400
    drafted = client.post(url + "/draft").json()
    assert "합계: 219,800원" in drafted["draft"] and drafted["status"] == "작성 중"
    done = client.patch(url, json={"confirmed": True}).json()
    assert done["confirmed"] is True and done["status"] == "작성 완료"
    edited = client.patch(url, json={"draft": drafted["draft"] + "\n추가"}).json()
    assert edited["confirmed"] is False and edited["status"] == "작성 중"


def test_rejects_bad_kind_and_nested_fields():
    from pydantic import ValidationError

    from app.domains.documents.schemas import DocumentCreate

    with pytest.raises(ValidationError):
        DocumentCreate(kind="계약서")
    with pytest.raises(ValidationError):
        DocumentCreate(kind="회의록", fields={"a": {"b": 1}})
    assert (
        DocumentCreate(kind="회의록", fields={"attendees": ["가", "나"], "n": 3}).fields["n"] == 3
    )
