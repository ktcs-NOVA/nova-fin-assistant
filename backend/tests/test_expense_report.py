"""지출 결과서 + 검수확인서 (기본 양식) 테스트.

앞부분은 DB 없이 도는 양식 계산, 뒷부분은 API 흐름(정산 건에서 만들기 → 직접 적을 칸 채우기 → 확인 → 보내기 →
관리자 화면에서 받기). API 쪽은 DB·시드가 없으면 건너뜁니다.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.db import SessionLocal
from app.core.security import create_token
from app.domains.documents import forms
from app.main import app
from app.models import Submission, User, WorkDocument

SUB = {
    "id": "S-2026-900", "type": "회의비", "purpose": "물류 지원사업 업무협의", "dept": "총무인사부",
    "account": "업무추진비", "amount": 24000,
    "expenses": [{
        "field": "회의 식대", "amount": 24000, "date": "2026-11-12", "payment": "법인카드",
        "merchant": "정담순두부", "meeting_purpose": "물류 지원사업 업무협의",
        "attendees": ["박철환", "김민수", "이영희", "정우성"],
    }],
    "trip": None,
}
TRIP_SUB = {
    "id": "S-2026-901", "type": "국내출장", "purpose": "부산 출장", "dept": "총무인사부", "account": "여비교통비",
    "trip": {"start_date": "2026-11-10", "end_date": "2026-11-11"},
    "expenses": [
        {"field": "숙박비", "amount": 180000, "date": "2026-11-10", "nights": 2},
        {"field": "철도운임", "amount": 59800, "date": "2026-11-10", "seat_class": "일반"},
    ],
}


def cells(form, sheet=0):
    return [c for row in form["sheets"][sheet]["table"]["rows"] for c in row]


# ── 양식 계산 (DB 불필요) ──
def test_amounts_and_dates_always_come_from_the_settlement():
    form = forms.build(SUB, {"detail_0": "아무 말", "amount": 999}, "박철환 (총무인사부)", date(2026, 11, 16))
    report, check = form["sheets"]
    assert report["title"] == "지출 결과서" and check["title"] == "검수확인서"
    row = report["table"]["rows"][0]
    assert [c["value"] for c in row] == ["1", "정담순두부 (회의 식대)", "아무 말", "26.11.12", "24,000원"]
    assert report["table"]["total"]["value"] == "24,000 원"
    assert report["date"] == "2026년 11월 16일"
    # 숫자·날짜 칸은 고칠 수 없는 자동 칸
    assert all(c["source"] == "auto" and "key" not in c for c in (row[0], row[1], row[3], row[4]))


def test_cells_are_tagged_by_who_fills_them():
    suggested = {**forms.suggest(SUB), "ai_keys": forms.ai_keys(SUB)}
    form = forms.build(SUB, suggested, "박철환 (총무인사부)")
    detail = form["sheets"][0]["table"]["rows"][0][2]
    assert detail["source"] == "ai" and detail["value"] == "물류 지원사업 업무협의 (4인)"
    # 직원이 고친 칸은 ai_keys 에서 빠지고 manual 로 바뀜
    edited = forms.build(SUB, {**suggested, "detail_0": "직접 적음", "ai_keys": ["use_0"]}, "w")
    assert edited["sheets"][0]["table"]["rows"][0][2]["source"] == "manual"
    inspector = form["sheets"][1]["signers"][0]["cell"]
    assert inspector["source"] == "manual" and inspector["required"] and inspector["value"] == ""
    assert form["sheets"][0]["signers"][1]["cell"]["source"] == "blank"  # 회계 담당 확인은 시스템 밖


def test_todo_lists_only_empty_required_cells():
    form = forms.build(SUB, {}, "w")
    assert [t["label"] for t in form["todo"]] == ["1번 상세내역", "1번 용도", "검사(수)자 소속·성명"]
    assert form["ready"] is False
    done = forms.build(SUB, {**forms.suggest(SUB), "inspector": "총무인사부 부서장 홍길동"}, "w")
    assert done["todo"] == [] and done["ready"] is True  # 특이 사항은 비워도 됨


def test_quantity_splits_only_when_it_divides_evenly():
    check = forms.build(TRIP_SUB, {}, "w")["sheets"][1]["table"]["rows"]
    assert [c["value"] for c in check[0][4:]] == ["2", "90,000", "180,000"]  # 2박 × 90,000
    assert [c["value"] for c in check[1][4:]] == ["1", "59,800", "59,800"]
    assert forms.suggest(TRIP_SUB)["detail_0"] == "26.11.10~26.11.11 출장 숙박비 (2박)"


def test_ai_polish_is_dropped_when_it_changes_numbers():
    from app.domains.documents.service import _keeps_facts

    draft = "26.11.10~26.11.11 출장 숙박비 (1박)"
    assert _keeps_facts(draft, "26.11.10~26.11.11 출장 숙박비(1박)")
    assert not _keeps_facts(draft, "출장 숙박비")  # 날짜·박수를 빼면 안 씀
    assert not _keeps_facts("업무협의 식대", "업무협의 식대 (4인)")  # 없는 숫자를 더해도 안 씀
    assert not _keeps_facts(draft, "  ")


def test_expected_documents_by_claim_type():
    assert forms.expected_kinds("국내출장") == ["지출결과서", "출장보고서", "출장원"]
    assert forms.expected_kinds("회의비") == ["지출결과서", "회의록"]
    assert forms.expected_kinds("기타 법인카드") == ["지출결과서"]


# ── API (DB 필요) ──
def auth(employee_no: str) -> dict:
    return {"Authorization": f"Bearer {create_token(employee_no)}"}


client = TestClient(app)
ME, OTHER, ADMIN = auth("E1001"), auth("E1002"), auth("A2001")

CLAIM = {
    "trip_type": "회의비", "grade": "직원 3급 이하", "settlement_date": "2026-11-12",
    "purpose": "테스트 결과서 업무협의", "account": "조직관리비",
    "items": [{
        "field": "회의 식대", "amount": 120000, "date": "2026-11-10", "time": "12:30", "payment": "법인카드",
        "merchant": "테스트식당", "category": "org", "meeting_purpose": "테스트 결과서 업무협의",
        "attendees": ["기획팀 노은비", "해운정책팀 황종원"], "participant_count": 2,
    }],
}


@pytest.fixture
def sub():
    try:
        with SessionLocal() as db:
            if db.scalar(select(User).where(User.employee_no == "E1001")) is None:
                pytest.skip("시드 전")
    except OperationalError:
        pytest.skip("DB 꺼짐")
    r = client.post("/api/submissions", json=CLAIM, headers=ME)
    assert r.status_code == 201, r.text
    code = r.json()["id"]
    yield code
    with SessionLocal() as db:
        row = db.scalar(select(Submission).where(Submission.code == code))
        for d in db.scalars(select(WorkDocument).where(WorkDocument.submission_id == row.id)):
            db.delete(d)
        for e in list(row.expenses):
            db.delete(e)
        db.delete(row)
        db.commit()


def make(code, headers=ME, kind="지출결과서", **extra):
    return client.post("/api/documents", json={"kind": kind, "submission_code": code, **extra}, headers=headers)


def test_report_is_created_from_my_settlement_once(sub):
    doc = make(sub).json()
    assert doc["kind"] == "지출결과서" and doc["submission_code"] == sub and doc["sent_at"] is None
    assert doc["title"] == "지출 결과서 · 테스트 결과서 업무협의"
    assert doc["fields"]["detail_0"] == "테스트 결과서 업무협의 (2인)"  # AI 칸은 처음부터 제안으로 채움
    assert make(sub).json()["id"] == doc["id"]  # 한 건에 한 부
    assert make(sub, OTHER).status_code == 404  # 남의 정산 건으로는 못 만듦
    assert client.post("/api/documents", json={"kind": "지출결과서"}, headers=ME).status_code == 400


def test_fill_confirm_send_then_admin_receives(sub):
    doc = make(sub).json()
    url = f"/api/documents/{doc['id']}"

    form = client.get(f"{url}/form", headers=ME).json()
    assert [t["key"] for t in form["todo"]] == ["inspector"]  # 직접 적을 칸은 검수자뿐
    assert client.patch(url, json={"confirmed": True}, headers=ME).status_code == 400  # 빈 칸이 있으면 확인 불가
    assert client.post(f"{url}/send", headers=ME).status_code == 400  # 확인 전에는 못 보냄

    fields = {**doc["fields"], "inspector": "기획팀 부서장 홍길동"}
    assert client.patch(url, json={"fields": fields, "confirmed": True}, headers=ME).json()["confirmed"] is True
    # 보내기 전에는 관리자에게 안 보이고, 받아야 할 서류로만 잡힘
    before = client.get(f"/api/admin/submissions/{sub}/documents", headers=ADMIN).json()
    assert before["documents"] == [] and before["missing"] == ["지출결과서", "회의록"]

    sent = client.post(f"{url}/send", headers=ME).json()
    assert sent["sent_at"] is not None
    got = client.get(f"/api/admin/submissions/{sub}/documents", headers=ADMIN).json()
    assert got["missing"] == ["회의록"]
    received = got["documents"][0]
    assert received["kind"] == "지출결과서" and received["writer"].startswith("노은비")
    assert received["form"]["sheets"][1]["signers"][0]["cell"]["value"] == "기획팀 부서장 홍길동"
    assert client.get(f"/api/admin/submissions/{sub}/documents", headers=ME).status_code == 403

    # 보낸 뒤에 고치면 확인·보냄이 풀려서 관리자가 옛 내용을 보지 않음
    changed = client.patch(url, json={"fields": {**fields, "remark": "추가"}}, headers=ME).json()
    assert changed["confirmed"] is False and changed["sent_at"] is None
    assert client.get(f"/api/admin/submissions/{sub}/documents", headers=ADMIN).json()["documents"] == []


def test_other_documents_can_be_attached_and_sent(sub):
    """회의록 같은 기존 서류도 정산 건에 붙여 보낼 수 있음."""
    fields = {"meeting_title": "테스트 회의", "meeting_date": "2026-11-10", "attendees": ["노은비", "황종원"], "notes": "논의"}
    doc = make(sub, kind="회의록", fields=fields).json()
    url = f"/api/documents/{doc['id']}"
    assert doc["submission_code"] == sub
    assert client.post(f"{url}/draft", headers=ME).status_code == 200
    assert client.patch(url, json={"confirmed": True}, headers=ME).status_code == 200
    assert client.post(f"{url}/send", headers=ME).json()["sent_at"] is not None
    got = client.get(f"/api/admin/submissions/{sub}/documents", headers=ADMIN).json()
    assert got["missing"] == ["지출결과서"] and got["documents"][0]["form"] is None
    assert "테스트 회의" in got["documents"][0]["draft"]

    loose = client.post("/api/documents", json={"kind": "회의록", "fields": fields}, headers=ME).json()
    assert client.post(f"/api/documents/{loose['id']}/send", headers=ME).status_code == 400  # 정산 건에 안 붙은 서류
    client.delete(f"/api/documents/{loose['id']}", headers=ME)
