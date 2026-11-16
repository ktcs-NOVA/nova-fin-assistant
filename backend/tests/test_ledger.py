"""지출내역 엑셀 테스트. 앞부분은 DB 없이 파일 내용 확인, 뒷부분은 내려받기 API(DB·시드가 없으면 건너뜀)."""

from datetime import date
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.db import SessionLocal
from app.core.security import create_token
from app.domains.ledger import excel
from app.main import app
from app.models import User

SUBS = [
    {"id": "S-2026-174", "type": "회의비", "purpose": "물류 지원사업 업무협의", "dept": "총무인사부", "submitter": "박철환",
     "account": "업무추진비", "status": "승인",
     "expenses": [{"field": "회의 식대", "amount": 24000, "date": "2026-11-12", "merchant": "정담순두부"}]},
    {"id": "S-2026-173", "type": "국내출장", "purpose": "부산 출장", "dept": "총무인사부", "submitter": "박철환",
     "account": None, "status": "검토 대기",
     "expenses": [{"field": "숙박비", "amount": 90000, "date": "2026-11-10"},
                  {"field": "철도운임", "amount": 59800, "date": "2026-11-10"}]},
]


def sheet(values=False, **kw):
    """values=True 면 수식 대신 파일에 함께 저장된 계산값을 읽음."""
    data = excel.build(SUBS, writer="박철환", dept="총무인사부", scope="내 정산 건", today=date(2026, 11, 16), **kw)
    return load_workbook(BytesIO(data), data_only=values).active


def test_one_row_per_expense_in_date_order():
    ws = sheet()
    assert [ws[f"{c}6"].value for c in "BCDEFGH"] == excel.HEADERS
    first = [ws[f"{c}7"].value for c in "BCDEFGH"]
    assert first == [1, "국내출장", "미입력", "총무인사부", "숙박비 · 부산 출장", 90000, "S-2026-173 · 26.11.10 · 검토 대기"]
    assert ws["F9"].value == "정담순두부 (회의 식대) · 물류 지원사업 업무협의"
    assert [ws[f"G{r}"].value for r in (7, 8, 9)] == [90000, 59800, 24000]  # 합치지 않고 건별 금액
    assert ws["F4"].value == "2026년 11월 10일 ~ 2026년 11월 12일" and ws["H5"].value == "2026년 11월 16일"


def test_subtotals_and_total_are_formulas():
    ws = sheet()
    assert ws["C10"].value == "소계" and ws["E10"].value == "국내출장"
    assert ws["G10"].value == '=SUMIF($C$7:$C$9,"국내출장",$G$7:$G$9)'
    assert ws["G11"].value == '=SUMIF($C$7:$C$9,"회의비",$G$7:$G$9)'
    assert ws["B12"].value == "합계" and ws["G12"].value == "=SUM(G10:G11)" and ws["H12"].value == "3건"
    assert ws["G7"].number_format == excel.MONEY
    # 수식을 계산하지 않는 미리보기에서도 숫자가 보이도록 계산값이 함께 저장됨
    shown = sheet(values=True)
    assert [shown[f"G{r}"].value for r in (10, 11, 12)] == [149800, 24000, 173800]


def test_admin_file_shows_who_spent():
    assert sheet(with_name=True)["E7"].value == "총무인사부 박철환"


def test_empty_ledger_still_opens():
    data = excel.build([], writer="w", dept="d", scope="내 정산 건", today=date(2026, 11, 16))
    ws = load_workbook(BytesIO(data)).active
    assert ws["F7"].value == "제출한 정산이 없습니다." and ws["G8"].value == "=0"


# ── API (DB 필요) ──
def auth(employee_no: str) -> dict:
    return {"Authorization": f"Bearer {create_token(employee_no)}"}


client = TestClient(app)


def test_download_mine_and_admin_only_for_all():
    try:
        with SessionLocal() as db:
            if db.scalar(select(User).where(User.employee_no == "E1001")) is None:
                pytest.skip("시드 전")
    except OperationalError:
        pytest.skip("DB 꺼짐")
    assert client.get("/api/ledger").status_code == 401
    r = client.get("/api/ledger", headers=auth("E1001"))
    assert r.status_code == 200 and r.headers["content-type"] == excel_type()
    assert "filename*=UTF-8''" in r.headers["content-disposition"]
    ws = load_workbook(BytesIO(r.content)).active
    assert ws["D4"].value == "한국해양진흥공사" and ws["H4"].value == "내 정산 건"
    # 내 것만: 집행부서 칸에 다른 부서가 섞이지 않음
    mine = {ws[f"E{row}"].value for row in range(7, ws.max_row + 1) if ws[f"C{row}"].value not in (None, "소계") and ws[f"B{row}"].value != "합계"}
    assert len(mine) <= 1
    assert client.get("/api/admin/ledger", headers=auth("E1001")).status_code == 403
    everyone = client.get("/api/admin/ledger", headers=auth("A2001"))
    assert everyone.status_code == 200 and load_workbook(BytesIO(everyone.content)).active["H4"].value == "전체 제출 건"


def excel_type():
    from app.domains.ledger.router import XLSX

    return XLSX
