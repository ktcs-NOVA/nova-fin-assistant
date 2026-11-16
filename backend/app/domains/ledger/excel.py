"""지출내역 엑셀 만들기 (기본 양식: KTcs 팀 활동비 지출내역의 표 구성을 가져옴).

제출한 정산 건의 지출 항목을 한 줄씩("건별 증빙과 동일한 금액, 합산기재 금지") 적고,
정산 유형별 소계와 합계는 엑셀 수식으로 넣어서 받은 사람이 줄을 고쳐도 다시 계산되게 합니다.
(계산한 값도 함께 저장해서, 수식을 계산하지 않는 미리보기에서도 숫자가 보입니다.)

`subs` 는 submissions.service.to_view() 가 돌려주는 제출 건 목록(dict)이라 DB 없이 테스트할 수 있습니다.
"""

from datetime import date
from io import BytesIO

import xlsxwriter

ORG = "한국해양진흥공사"
HEADERS = ["No", "구분", "집행유형", "집행부서", "내용", "금액", "비고(증빙번호 등)"]
COLUMNS = "BCDEFGH"
WIDTHS = {"A": 3, "B": 6, "C": 14, "D": 16, "E": 22, "F": 52, "G": 16, "H": 34, "I": 4, "J": 18, "K": 18}
ACCOUNTS = ["여비교통비", "업무추진비", "조직관리비", "소모품비", "도서인쇄비", "통신비", "교육훈련비", "지급수수료", "차량유지비"]
FIRST_ROW = 7  # 표의 첫 내용 줄 (6행이 머리줄)
MONEY = "#,##0;(-)#,##0;-"
HEAD_FILL = "#D9E2F3"
SOFT_FILL = "#F2F2F2"


def _short(s) -> str:
    try:
        d = date.fromisoformat(str(s)[:10])
    except ValueError:
        return str(s or "")
    return f"{d.year % 100:02d}.{d.month:02d}.{d.day:02d}"


def _long(d: date) -> str:
    return f"{d.year}년 {d.month:02d}월 {d.day:02d}일"


def ledger_rows(subs: list[dict], with_name: bool = False) -> list[dict]:
    """제출 건 목록 → 지출 한 건이 한 줄. 지출일 순(같은 날은 제출 번호 순)."""
    rows = []
    for s in subs:
        dept = str(s.get("dept") or "")
        if with_name:
            dept = f"{dept} {s.get('submitter') or ''}".strip()
        for e in s.get("expenses") or []:
            field = str(e.get("field") or "기타")
            merchant = str(e.get("merchant") or "").strip()
            item = f"{merchant} ({field})" if merchant else field
            rows.append({
                "type": str(s.get("type") or ""),
                "account": str(s.get("account") or "") or "미입력",
                "dept": dept,
                "content": f"{item} · {s.get('purpose') or ''}".rstrip(" ·"),
                "amount": int(e.get("amount") or 0),
                "note": " · ".join(x for x in (str(s.get("id") or ""), _short(e.get("date")), str(s.get("status") or "")) if x),
                "date": str(e.get("date") or ""),
                "code": str(s.get("id") or ""),
            })
    rows.sort(key=lambda r: (r["date"], r["code"]))
    return rows


def build(subs: list[dict], *, writer: str, dept: str, scope: str, today: date | None = None,
          with_name: bool = False) -> bytes:
    """지출내역 엑셀 파일(.xlsx) 바이트."""
    today = today or date.today()
    rows = ledger_rows(subs, with_name)
    out = BytesIO()
    wb = xlsxwriter.Workbook(out, {"in_memory": True})
    ws = wb.add_worksheet("지출내역")
    for col, width in WIDTHS.items():
        ws.set_column(f"{col}:{col}", width)

    formats: dict[tuple, object] = {}

    def fmt(*, bold=False, fill=None, align="center", money=False, border=True, size=10):
        """칸 서식 (같은 조합은 한 번만 만듦)."""
        key = (bold, fill, align, money, border, size)
        if key not in formats:
            spec = {"font_size": size, "bold": bold, "align": align, "valign": "vcenter", "text_wrap": border}
            if border:
                spec |= {"border": 1, "border_color": "#7F7F7F"}
            if fill:
                spec["bg_color"] = fill
            if money:
                spec["num_format"] = MONEY
            formats[key] = wb.add_format(spec)
        return formats[key]

    ws.set_row(0, 32)
    ws.write("B1", "경비 정산 지출내역", fmt(bold=True, align="left", border=False, size=20))
    ws.write("B2", "(*) (신용카드매출전표 등) 건별 증빙과 동일한 금액 기재, 합산기재 금지",
             fmt(bold=True, align="left", border=False, size=12))

    dates = sorted(r["date"] for r in rows if r["date"])
    period = f"{_long(date.fromisoformat(dates[0][:10]))} ~ {_long(date.fromisoformat(dates[-1][:10]))}" if dates else "-"
    info = [("C4", "기관명 :", "D4", ORG), ("E4", "해당기간 :", "F4", period), ("G4", "범위 :", "H4", scope),
            ("C5", "부서 :", "D5", dept), ("E5", "작성자 :", "F5", writer), ("G5", "출력일 :", "H5", _long(today))]
    for label_at, label, value_at, value in info:
        ws.write(label_at, label, fmt(bold=True, align="right", border=False))
        ws.write(value_at, value, fmt(bold=True, align="left", border=False))

    ws.set_row(5, 22)
    for col, title in zip(COLUMNS, HEADERS, strict=True):
        ws.write(f"{col}6", title, fmt(bold=True, fill=HEAD_FILL))

    r = FIRST_ROW
    if not rows:
        for col in COLUMNS:
            ws.write(f"{col}{r}", "제출한 정산이 없습니다." if col == "F" else "", fmt())
        r += 1
    for n, row in enumerate(rows, start=1):
        ws.write(f"B{r}", n, fmt(bold=True))
        ws.write(f"C{r}", row["type"], fmt())
        ws.write(f"D{r}", row["account"], fmt(fill=SOFT_FILL))
        ws.write(f"E{r}", row["dept"], fmt(fill=SOFT_FILL))
        ws.write(f"F{r}", row["content"], fmt(align="left"))
        ws.write_number(f"G{r}", row["amount"], fmt(align="right", money=True))
        ws.write(f"H{r}", row["note"], fmt())
        r += 1
    last = r - 1

    # 정산 유형별 소계 + 합계. 수식으로 넣어 줄을 고쳐도 다시 계산되게 하고,
    # 계산한 값도 함께 저장해서 수식을 계산하지 않는 미리보기(휴대폰·메신저)에서도 숫자가 보이게 합니다.
    c_range, g_range = f"$C${FIRST_ROW}:$C${last}", f"$G${FIRST_ROW}:$G${last}"
    types = list(dict.fromkeys(row["type"] for row in rows))
    first_sub = r
    for t in types:
        for col in COLUMNS:
            ws.write(f"{col}{r}", "", fmt(bold=True))
        ws.write(f"C{r}", "소계", fmt(bold=True))
        ws.write(f"E{r}", t, fmt(bold=True))
        subtotal = sum(row["amount"] for row in rows if row["type"] == t)
        ws.write_formula(f"G{r}", f'=SUMIF({c_range},"{t}",{g_range})', fmt(bold=True, align="right", money=True), subtotal)
        ws.write(f"H{r}", f"{t} 소계", fmt(bold=True))
        r += 1
    head = fmt(bold=True, fill=HEAD_FILL)
    ws.write(f"B{r}", "합계", head)
    ws.merge_range(f"C{r}:F{r}", "승인·검토 대기 건 합계 (반려한 정산은 제외)", head)
    total = sum(row["amount"] for row in rows)
    ws.write_formula(f"G{r}", f"=SUM(G{first_sub}:G{r - 1})" if types else "=0",
                     fmt(bold=True, fill=HEAD_FILL, align="right", money=True), total)
    ws.write(f"H{r}", f"{len(rows)}건", head)
    ws.write(f"B{r + 2}",
             "(*) 금액·지출일은 제출한 정산 건 그대로입니다. 비고의 번호(S-…)는 정산 제출 번호이고, "
             "같은 번호의 지출 결과서·검수확인서가 증빙입니다.",
             fmt(align="left", border=False))

    # 오른쪽 참고 목록 (원 양식의 (*)집행유형 구분)
    for col, title, items in (("J", "(*)집행유형 구분", ACCOUNTS), ("K", "(*)구분", ["국내출장", "회의비", "기타 법인카드"])):
        ws.write(f"{col}{FIRST_ROW}", title, fmt(bold=True, align="left", border=False))
        for i, item in enumerate(items, start=1):
            ws.write(f"{col}{FIRST_ROW + i}", item, fmt(bold=True, fill=SOFT_FILL))

    ws.freeze_panes(FIRST_ROW - 1, 0)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    wb.close()
    return out.getvalue()
