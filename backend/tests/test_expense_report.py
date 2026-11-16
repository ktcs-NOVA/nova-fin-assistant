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


def block(form, kind, sheet=0, nth=0):
    """한 장에서 kind 종류 블록의 nth 번째."""
    return [b for b in form["sheets"][sheet]["blocks"] if b["type"] == kind][nth]


def rows(form, sheet=0, nth=0):
    return block(form, "table", sheet, nth)["rows"]


def report(sub=SUB, fields=None, writer="박철환 (총무인사부)", today=date(2026, 11, 16)):
    return forms.build(forms.KIND, sub, fields or {}, writer, today)


# ── 양식 계산 (DB 불필요) ──
def test_amounts_and_dates_always_come_from_the_settlement():
    form = report(fields={"detail_0": "아무 말", "amount": 999})
    assert [s["title"] for s in form["sheets"]] == ["지출 결과서", "검수확인서"]
    row = rows(form)[0]
    assert [c["value"] for c in row] == ["1", "정담순두부 (회의 식대)", "아무 말", "26.11.12", "24,000원"]
    assert block(form, "table")["total"]["value"] == "24,000 원"
    assert block(form, "note", nth=1)["text"] == "2026년 11월 16일"
    # 숫자·날짜 칸은 고칠 수 없는 자동 칸
    assert all(c["source"] == "auto" and "key" not in c for c in (row[0], row[1], row[3], row[4]))


def test_cells_are_tagged_by_who_fills_them():
    suggested = forms.initial_fields(forms.KIND, SUB)
    form = report(fields=suggested)
    detail = rows(form)[0][2]
    assert detail["source"] == "ai" and detail["value"] == "물류 지원사업 업무협의 (4인)"
    # 직원이 고친 칸은 ai_keys 에서 빠지고 manual 로 바뀜
    edited = report(fields={**suggested, "detail_0": "직접 적음", "ai_keys": ["use_0"]})
    assert rows(edited)[0][2]["source"] == "manual"
    inspector = block(form, "signers", sheet=1)["rows"][0]["cell"]
    assert inspector["source"] == "manual" and inspector["required"] and inspector["value"] == ""
    assert block(form, "signers")["rows"][1]["cell"]["source"] == "blank"  # 회계 담당 확인은 시스템 밖


def test_todo_lists_only_empty_required_cells():
    form = report()
    assert [t["label"] for t in form["todo"]] == ["1번 상세내역", "1번 용도", "검사(수)자 소속·성명"]
    assert form["ready"] is False
    done = report(fields={**forms.suggest(SUB), "inspector": "총무인사부 부서장 홍길동"})
    assert done["todo"] == [] and done["ready"] is True  # 특이 사항은 비워도 됨


def test_quantity_splits_only_when_it_divides_evenly():
    check = rows(report(TRIP_SUB), sheet=1)
    assert [c["value"] for c in check[0][4:]] == ["2", "90,000", "180,000"]  # 2박 × 90,000
    assert [c["value"] for c in check[1][4:]] == ["1", "59,800", "59,800"]
    assert forms.suggest(TRIP_SUB)["detail_0"] == "26.11.10~26.11.11 출장 숙박비 (2박)"


def test_evidence_carries_receipt_photo_when_the_expense_has_one():
    sub = {**SUB, "expenses": [{**SUB["expenses"][0], "receipt_id": 7}]}
    item = block(report(sub), "evidence", sheet=1)["items"][0]
    assert item == {"date": "26.11.12", "label": "업무추진비 / 정담순두부 (회의 식대)", "amount": "24,000원",
                    "payment": "법인카드", "receipt_id": 7}
    assert block(report(), "evidence", sheet=1)["items"][0]["receipt_id"] is None


def test_minutes_fill_roster_and_amounts_from_the_meeting():
    sub = {**SUB, "expenses": [{**SUB["expenses"][0], "time": "12:31",
                                "attendees": ["총무인사부 박철환", "부산항만공사 이영희 과장", "김민수"]}]}
    form = forms.build(forms.MINUTES, sub, {}, "w")
    info = {r["label"]: r["cell"]["value"] for r in block(form, "info")["rows"]}
    assert info == {"회의주제": "물류 지원사업 업무협의", "회의일시": "2026년 11월 12일, 12:31", "회의장소": "정담순두부"}
    roster = rows(form)  # 한 줄에 두 명, 소속·성명·서명
    assert [c["value"] for c in roster[0]] == ["총무인사부", "박철환", "(인)", "부산항만공사", "이영희 과장", "(인)"]
    assert [c["value"] for c in roster[1]] == ["", "김민수", "(인)", "", "", ""]
    amount = block(form, "table", nth=1)
    assert [c["value"] for c in amount["rows"][0]] == ["회의 식대", "24,000", "박철환, 이영희 과장, 김민수", "3명"]
    assert amount["total"]["value"] == "24,000 원"
    assert "1인당 약 8,000원" in block(form, "note")["text"]
    # 직접 적을 칸은 회의 내용 하나
    assert [t["label"] for t in form["todo"]] == ["회의 내용"]
    content = block(form, "field")["cell"]
    assert content["source"] == "manual" and content["multiline"]
    polished = forms.build(forms.MINUTES, sub, {"content": "다듬은 글", "ai_keys": ["content"]}, "w")
    assert block(polished, "field")["cell"]["source"] == "ai" and polished["ready"]


def test_trip_report_asks_for_destination_and_content():
    sub = {**TRIP_SUB, "submitter": "박철환", "trip": {**TRIP_SUB["trip"], "destination": "광역시"}}
    form = forms.build(forms.TRIP_REPORT, sub, forms.initial_fields(forms.TRIP_REPORT, sub), "w")
    info = {r["label"]: r["cell"]["value"] for r in block(form, "info")["rows"]}
    assert info["출장일자"] == "2026년 11월 10일 ~ 2026년 11월 11일 (1박 2일)"
    assert info["출장지"] == ""  # '광역시' 는 지역 구분이라 출장지로 쓰지 않음
    assert [t["label"] for t in form["todo"]] == ["출장지", "출장 내용"]
    assert [c["value"] for c in rows(form)[0][:3]] == ["총무인사부", "박철환", "(인)"]
    amount = block(form, "table", nth=1)["rows"]
    assert [c["value"] for c in amount[0]] == ["숙박비", "180,000", "박철환", "2박"]
    named = {**sub, "trip": {**sub["trip"], "destination": "부산 영도"}}
    assert forms.initial_fields(forms.TRIP_REPORT, named, {"work_notes": "점검"}) == {"destination": "부산 영도", "content": "점검"}


def test_ai_polish_is_dropped_when_it_changes_numbers():
    from app.domains.documents.service import _keeps_facts

    draft = "26.11.10~26.11.11 출장 숙박비 (1박)"
    assert _keeps_facts(draft, "26.11.10~26.11.11 출장 숙박비(1박)")
    assert not _keeps_facts(draft, "출장 숙박비")  # 날짜·박수를 빼면 안 씀
    assert not _keeps_facts("업무협의 식대", "업무협의 식대 (4인)")  # 없는 숫자를 더해도 안 씀
    assert not _keeps_facts(draft, "  ")


def test_expected_documents_by_claim_type():
    assert forms.expected_kinds("국내출장") == ["지출결과서", "출장보고서"]
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
    signers = [b for b in received["form"]["sheets"][1]["blocks"] if b["type"] == "signers"][0]
    assert signers["rows"][0]["cell"]["value"] == "기획팀 부서장 홍길동"
    assert client.get(f"/api/admin/submissions/{sub}/documents", headers=ME).status_code == 403

    # 보낸 뒤에 고치면 확인·보냄이 풀려서 관리자가 옛 내용을 보지 않음
    changed = client.patch(url, json={"fields": {**fields, "remark": "추가"}}, headers=ME).json()
    assert changed["confirmed"] is False and changed["sent_at"] is None
    assert client.get(f"/api/admin/submissions/{sub}/documents", headers=ADMIN).json()["documents"] == []


def test_minutes_from_a_settlement_is_a_form_and_can_be_sent(sub):
    """정산 건에서 만든 회의록은 양식으로: 회의 내용만 적으면 확인·보내기가 됨."""
    doc = make(sub, kind="회의록", fields={"notes": "일정 논의"}).json()
    url = f"/api/documents/{doc['id']}"
    assert doc["submission_code"] == sub and doc["fields"] == {"content": "일정 논의"}
    assert make(sub, kind="회의록").json()["id"] == doc["id"]  # 한 건에 한 부
    assert client.post(f"{url}/draft", headers=ME).status_code == 400  # 줄글 초안이 아니라 양식

    assert client.patch(url, json={"fields": {"content": ""}}, headers=ME).status_code == 200
    assert client.patch(url, json={"confirmed": True}, headers=ME).status_code == 400  # 회의 내용이 비어 있음
    assert client.post(f"{url}/fill", headers=ME).status_code == 400  # 다듬을 메모가 없음
    client.patch(url, json={"fields": {"content": "일정 논의함"}, "confirmed": True}, headers=ME)
    assert client.post(f"{url}/send", headers=ME).json()["sent_at"] is not None

    got = client.get(f"/api/admin/submissions/{sub}/documents", headers=ADMIN).json()
    assert got["missing"] == ["지출결과서"]
    form = got["documents"][0]["form"]
    assert form["sheets"][0]["title"] == "회 의 록"
    assert [b for b in form["sheets"][0]["blocks"] if b["type"] == "field"][0]["cell"]["value"] == "일정 논의함"


def test_loose_documents_keep_the_draft_flow_and_cannot_be_sent():
    """정산 건 없이 따로 쓴 회의록은 예전처럼 줄글 초안이고, 관리자에게 보낼 수 없음."""
    try:
        with SessionLocal() as db:
            if db.scalar(select(User).where(User.employee_no == "E1001")) is None:
                pytest.skip("시드 전")
    except OperationalError:
        pytest.skip("DB 꺼짐")
    fields = {"meeting_title": "테스트 회의", "meeting_date": "2026-11-10", "attendees": ["노은비", "황종원"], "notes": "논의"}
    loose = client.post("/api/documents", json={"kind": "회의록", "fields": fields}, headers=ME).json()
    url = f"/api/documents/{loose['id']}"
    try:
        assert client.post(f"{url}/draft", headers=ME).status_code == 200
        assert client.get(f"{url}/form", headers=ME).status_code == 400
        assert client.patch(url, json={"confirmed": True}, headers=ME).status_code == 200
        assert client.post(f"{url}/send", headers=ME).status_code == 400  # 정산 건에 안 붙은 서류
    finally:
        client.delete(url, headers=ME)


def test_receipt_photo_is_kept_and_shown_only_to_owner_and_admin(sub):
    """로그인하고 올린 영수증은 보관되고, 정산 건에 실린 번호가 증빙 칸으로 감. 남의 영수증 번호는 빠짐."""
    from app.domains.receipt import service as receipts
    from app.models import Receipt

    png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    body = {"filename": "t.png", "media_type": "image/png", "image_base64": png}
    assert "receipt_id" not in client.post("/api/receipt", json=body).json()  # 로그인 없이 올리면 보관하지 않음
    mine = client.post("/api/receipt", json=body, headers=ME).json()["receipt_id"]
    theirs = client.post("/api/receipt", json=body, headers=OTHER).json()["receipt_id"]
    try:
        assert client.get(f"/api/receipts/{mine}/image", headers=ME).headers["content-type"] == "image/png"
        assert client.get(f"/api/receipts/{mine}/image", headers=ADMIN).status_code == 200
        assert client.get(f"/api/receipts/{mine}/image", headers=OTHER).status_code == 404
        assert client.get(f"/api/receipts/{mine}/image").status_code == 401

        def evidence(receipt_id):
            claim = {**CLAIM, "items": [{**CLAIM["items"][0], "receipt_id": receipt_id}]}
            code = client.post("/api/submissions", json=claim, headers=ME).json()["id"]
            try:
                doc = make(code).json()
                form = client.get(f"/api/documents/{doc['id']}/form", headers=ME).json()
                return [b for b in form["sheets"][1]["blocks"] if b["type"] == "evidence"][0]["items"][0]["receipt_id"]
            finally:
                with SessionLocal() as db:
                    row = db.scalar(select(Submission).where(Submission.code == code))
                    for d in db.scalars(select(WorkDocument).where(WorkDocument.submission_id == row.id)):
                        db.delete(d)
                    for e in list(row.expenses):
                        db.delete(e)
                    db.delete(row)
                    db.commit()

        assert evidence(mine) == mine
        assert evidence(theirs) is None  # 남이 올린 영수증 번호는 증빙으로 붙지 않음
    finally:
        with SessionLocal() as db:
            for rid in (mine, theirs):
                row = db.get(Receipt, rid)
                (receipts.UPLOAD_DIR / row.image_path).unlink(missing_ok=True)
                db.delete(row)
            db.commit()

