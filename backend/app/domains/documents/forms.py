"""기본 양식 3종: 지출 결과서(+검수확인서) · 회의록 · 출장보고서.
(표준 라이브러리만 사용 — 단위 테스트가 DB·API 키 없이 돕니다.)

양식의 칸 구성은 여기 한 곳에서 정합니다. 칸마다 값이 어디서 오는지(source)를 붙여서
화면이 색으로 구분하고, 직원이 직접 적어야 하는 칸만 골라 안내할 수 있게 합니다.

  auto    정산 건에서 그대로 가져온 값 (금액·날짜·건명·참석자 …). 서류에서 고칠 수 없음
  ai      AI 가 쓰거나 다듬은 문구. 직원이 고칠 수 있음
  manual  직원이 직접 적는 칸 (검수자, 회의 내용, 출장지 …)
  blank   시스템 밖에서 채우는 칸 (서명·날인, 사진)

양식 한 부는 장(sheet) 여러 개, 한 장은 위에서 아래로 쌓이는 블록(block) 목록입니다.
  info      [{label, cell}]                       머리표 (건명·일시·장소 …)
  table     {caption?, columns, rows, total?}     품목표 · 명단 · 집행금액
  field     {label, cell}                         넓은 글 칸 (회의 내용 · 출장 내용)
  note      {text, style}                         안내 문구 · 날짜
  signers   [{role, cell}]                        작성자 · 확인자 · 검수자
  evidence  {title, items}                        증빙 (영수증 사진이 있으면 receipt_id)
  photos    {title, hint}                         인쇄한 뒤 붙이는 사진 자리
장에 `approval` ({label, roles}) 이 있으면 제목 오른쪽 위에 결재란 표를 그립니다 (지출 결과서 · 출장보고서).
결재란은 인쇄한 뒤 서명·날인하는 빈 칸이고, 결재가 실제로 넘어가는 기능은 없습니다.

`sub` 는 submissions.service.to_view() 가 돌려주는 제출 건 한 건(dict), `fields` 는 서류에 저장된
직원 입력값({"detail_0": …, "inspector": …, "content": …, "ai_keys": [...]}) 입니다.
금액·날짜는 항상 sub 에서 다시 읽으므로 서류에서 숫자가 달라질 수 없습니다.
"""

from datetime import date

KIND = "지출결과서"
MINUTES = "회의록"
TRIP_REPORT = "출장보고서"
FORM_KINDS = (KIND, MINUTES, TRIP_REPORT)
ORG = "한국해양진흥공사"

AUTO, AI, MANUAL, BLANK = "auto", "ai", "manual", "blank"
_REGION_GROUPS = {"서울", "광역시", "기타"}  # 숙박비 상한용 지역 구분이라 출장지 이름이 아님


def expected_kinds(sub_type: str) -> list[str]:
    """정산 유형별로 함께 내야 하는 서류 (관리자 화면의 '받은 서류 / 아직 안 온 서류' 기준)."""
    if "출장" in (sub_type or ""):
        return [KIND, TRIP_REPORT]
    if sub_type == "회의비":
        return [KIND, MINUTES]
    return [KIND]


# ---------------------------------------------------------------------------
# 표기
# ---------------------------------------------------------------------------
def won(n) -> str:
    return f"{int(n or 0):,}"


def _date(s) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def short_date(s) -> str:
    """'2026-11-12' → '26.11.12' (원 양식의 지출날짜 표기)."""
    d = _date(s)
    return f"{d.year % 100:02d}.{d.month:02d}.{d.day:02d}" if d else str(s or "")


def long_date(d) -> str:
    d = d if isinstance(d, date) else _date(d)
    return f"{d.year}년 {d.month}월 {d.day}일" if d else ""


def _period(start, end) -> str:
    a, b = _date(start), _date(end)
    if not a:
        return ""
    if not b or b == a:
        return f"{long_date(a)} (당일)"
    nights = (b - a).days
    return f"{long_date(a)} ~ {long_date(b)} ({nights}박 {nights + 1}일)"


def _expenses(sub: dict) -> list[dict]:
    return list(sub.get("expenses") or [])


def _total(sub: dict) -> int:
    return sum(int(e.get("amount") or 0) for e in _expenses(sub))


def _qty(e: dict) -> int:
    """수량: 숙박은 박수, 일수 정액은 일수, 나머지는 1. 금액이 나누어떨어질 때만 씁니다."""
    for key in ("nights", "days"):
        try:
            n = int(e.get(key) or 0)
        except (TypeError, ValueError):
            n = 0
        if n > 1 and int(e.get("amount") or 0) % n == 0:
            return n
    return 1


def _item_name(e: dict) -> str:
    """품명: 가맹점이 있으면 '가맹점 (항목)', 없으면 항목."""
    field = str(e.get("field") or "기타")
    merchant = str(e.get("merchant") or "").strip()
    return f"{merchant} ({field})" if merchant else field


def _split_person(text: str) -> tuple[str, str]:
    """'총무인사부 박철환' → ('총무인사부', '박철환'). 소속 없이 이름만 있으면 ('', 이름)."""
    parts = str(text or "").split()
    if len(parts) <= 1:
        return "", "".join(parts)
    return parts[0], " ".join(parts[1:])


# ---------------------------------------------------------------------------
# 칸
# ---------------------------------------------------------------------------
def _cell(value="", source=AUTO, align=None) -> dict:
    cell = {"value": "" if value is None else str(value), "source": source}
    if align:
        cell["align"] = align
    return cell


def _edit(fields: dict, key: str, label: str, *, required=False, placeholder="", ai=False,
          multiline=False, limit=60) -> dict:
    """고칠 수 있는 칸. ai=True 면 AI 가 채우는 칸이고, 직원이 고치면(ai_keys 에서 빠지면) manual 이 됩니다."""
    value = str(fields.get(key) or "").strip()
    from_ai = key in (fields.get("ai_keys") or []) if value else ai
    return {
        "value": value, "source": AI if from_ai else MANUAL, "key": key, "label": label,
        "required": required, "placeholder": placeholder, "ai": ai, "multiline": multiline, "limit": limit,
    }


def _amount_table(sub: dict, who: str, headcount: int, remark) -> dict:
    """집행금액 표: 항목 · 금액 · 대상자 · 비고 (+총계)."""
    rows = [
        [
            _cell(e.get("field") or "기타"),
            _cell(won(e.get("amount")), align="right"),
            _cell(who),
            _cell(remark(e) if callable(remark) else remark, align="center"),
        ]
        for e in _expenses(sub)
    ]
    return {
        "type": "table", "caption": "집행금액",
        "columns": [{"label": "항목", "width": "24%"}, {"label": "금액", "width": "18%"},
                    {"label": "대상자", "width": "42%"}, {"label": "비고", "width": "16%"}],
        "rows": rows,
        "total": {"label": "총 계", "value": f"{won(_total(sub))} 원", "span": 1},
    }


def _roster(caption: str, people: list[tuple[str, str]], min_rows: int = 2) -> dict:
    """명단 표: 소속 · 성명 · 서명 을 한 줄에 두 명씩."""
    slots = people + [("", "")] * max(0, min_rows * 2 - len(people))
    if len(slots) % 2:
        slots.append(("", ""))
    rows = []
    for i in range(0, len(slots), 2):
        row = []
        for dept, name in slots[i:i + 2]:
            row += [_cell(dept, align="center"), _cell(name, align="center"), _cell("(인)" if name else "", BLANK, "center")]
        rows.append(row)
    cols = [{"label": "소속", "width": "20%"}, {"label": "성명", "width": "18%"}, {"label": "서명", "width": "12%"}]
    return {"type": "table", "caption": caption, "columns": cols * 2, "rows": rows}


def _evidence(sub: dict, title: str, category: str = "") -> dict:
    items = []
    for e in _expenses(sub):
        label = f"{category} / {_item_name(e)}" if category else _item_name(e)
        items.append({
            "date": short_date(e.get("date")), "label": label, "amount": f"{won(e.get('amount'))}원",
            "payment": str(e.get("payment") or ""), "receipt_id": e.get("receipt_id"),
        })
    return {"type": "evidence", "title": title, "items": items}


# ---------------------------------------------------------------------------
# 지출 결과서 + 검수확인서
# ---------------------------------------------------------------------------
def suggest(sub: dict) -> dict[str, str]:
    """지출결과서 AI 칸(상세내역·용도)의 기본 제안. 정산 건에 있는 사실만 조합하고, 없는 내용은 만들지 않습니다."""
    out: dict[str, str] = {}
    sub_type = str(sub.get("type") or "")
    trip = sub.get("trip") or {}
    for i, e in enumerate(_expenses(sub)):
        field = str(e.get("field") or "기타")
        purpose = str(e.get("meeting_purpose") or "").strip()
        people = e.get("attendees") or []
        count = e.get("participant_count") or len(people)
        if purpose:
            detail = purpose + (f" ({count}인)" if count else "")
            use = f"{purpose} {field}"
        elif "출장" in sub_type:
            span = ""
            if trip.get("start_date") and trip.get("end_date"):
                span = f"{short_date(trip['start_date'])}~{short_date(trip['end_date'])} "
            extra = []
            if e.get("seat_class"):
                extra.append(str(e["seat_class"]))
            if e.get("nights"):
                extra.append(f"{e['nights']}박")
            tail = f" ({', '.join(extra)})" if extra else ""
            detail = f"{span}출장 {field}{tail}"
            use = f"출장 {field}"
        else:
            merchant = str(e.get("merchant") or "").strip()
            detail = f"{merchant} {field}".strip()
            use = f"{sub.get('purpose') or field}"
        out[f"detail_{i}"] = detail[:60]
        out[f"use_{i}"] = use[:60]
    return out


# 결재란: 제목 오른쪽 위의 작은 표. 직위 줄 아래가 서명·날인 칸 (인쇄한 뒤 채움)
APPROVAL = {"label": "결재", "roles": ["담당", "팀장", "부서장"]}


def _report(sub: dict, fields: dict, writer: str, today: date) -> list[dict]:
    total = _total(sub)
    category = str(sub.get("account") or sub.get("type") or "")
    report_rows, check_rows = [], []
    for i, e in enumerate(_expenses(sub)):
        amount = int(e.get("amount") or 0)
        qty = _qty(e)
        report_rows.append([
            _cell(i + 1, align="center"),
            _cell(_item_name(e)),
            _edit(fields, f"detail_{i}", f"{i + 1}번 상세내역", required=True, ai=True,
                  placeholder="예: 외부 기관 업무협의 식대 (4인)"),
            _cell(short_date(e.get("date")), align="center"),
            _cell(f"{won(amount)}원", align="right"),
        ])
        check_rows.append([
            _cell(i + 1, align="center"),
            _cell(category, align="center"),
            _cell(_item_name(e)),
            _edit(fields, f"use_{i}", f"{i + 1}번 용도", required=True, ai=True, placeholder="예: 업무협의 식대"),
            _cell(qty, align="center"),
            _cell(won(amount // qty), align="right"),
            _cell(won(amount), align="right"),
        ])

    return [
        {"title": "지출 결과서", "approval": APPROVAL, "blocks": [
            {"type": "info", "rows": [
                {"label": "기관명", "cell": _cell(ORG)},
                {"label": "건명", "cell": _cell(sub.get("purpose"))},
                {"label": "부서", "cell": _cell(sub.get("dept"))},
                {"label": "정산 유형 · 제출 번호", "cell": _cell(f"{sub.get('type') or ''} · {sub.get('id') or ''}")},
            ]},
            {"type": "table",
             "columns": [{"label": "번호", "width": "8%"}, {"label": "내용(품명)", "width": "26%"},
                         {"label": "상세내역", "width": "34%"}, {"label": "지출날짜", "width": "14%"},
                         {"label": "금액", "width": "18%"}],
             "rows": report_rows,
             "total": {"label": "소 계", "value": f"{won(total)} 원", "span": 4}},
            {"type": "info", "rows": [
                {"label": "특이 사항", "cell": _edit(fields, "remark", "특이 사항", placeholder="없으면 비워 두세요")},
            ]},
            {"type": "note", "text": "위와 같이 지출 결과를 보고합니다.", "style": "center"},
            {"type": "note", "text": long_date(today), "style": "date"},
            {"type": "signers", "rows": [
                {"role": "작성자", "cell": _cell(writer)},
                {"role": "확인자 (회계 담당)", "cell": _cell("", BLANK)},
            ]},
            {"type": "note", "text": "※ 첨부. 지출 증빙(검수확인서, 회의록, 출장보고서 등)", "style": "foot"},
        ]},
        {"title": "검수확인서", "blocks": [
            {"type": "info", "rows": [
                {"label": "건명", "cell": _cell(sub.get("purpose"))},
                {"label": "부서", "cell": _cell(sub.get("dept"))},
            ]},
            {"type": "table",
             "columns": [{"label": "순번", "width": "7%"}, {"label": "구분", "width": "14%"},
                         {"label": "품명", "width": "25%"}, {"label": "용도", "width": "24%"},
                         {"label": "수량", "width": "7%"}, {"label": "단가(원)", "width": "11%"},
                         {"label": "금액(원)", "width": "12%"}],
             "rows": check_rows,
             "total": {"label": "합 계", "value": f"{won(total)} 원", "span": 6}},
            {"type": "note", "text": "상기와 같이 검사(수)함", "style": "center"},
            {"type": "note", "text": long_date(today), "style": "date"},
            {"type": "signers", "rows": [
                {"role": "검사(수)자", "cell": _edit(fields, "inspector", "검사(수)자 소속·성명", required=True,
                                                 placeholder="예: 총무인사부 부서장 홍길동")},
            ]},
            _evidence(sub, "검 수 증 빙", category),
        ]},
    ]


# ---------------------------------------------------------------------------
# 회의록
# ---------------------------------------------------------------------------
def _minutes(sub: dict, fields: dict) -> list[dict]:
    rows = _expenses(sub)
    first = rows[0] if rows else {}
    people = [str(p) for p in (first.get("attendees") or [])]
    count = int(first.get("participant_count") or len(people) or 0)
    when = long_date(first.get("date"))
    if first.get("time"):
        when += f", {first['time']}"
    total = _total(sub)
    blocks = [
        {"type": "info", "rows": [
            {"label": "회의주제", "cell": _cell(first.get("meeting_purpose") or sub.get("purpose"))},
            {"label": "회의일시", "cell": _cell(when)},
            {"label": "회의장소", "cell": _cell(first.get("merchant"))},
        ]},
        _roster("참여자 명단", [_split_person(p) for p in people]),
        {"type": "field", "label": "회의 내용", "cell": _edit(
            fields, "content", "회의 내용", required=True, multiline=True, limit=2000,
            placeholder="논의한 내용을 메모처럼 편하게 적어 주세요. 적은 뒤 ‘AI로 문장 다듬기’를 누르면 회의록 문체로 정리해 드려요.")},
        _amount_table(sub, ", ".join(_split_person(p)[1] for p in people), count, f"{count}명" if count else ""),
    ]
    if count and total:
        blocks.append({"type": "note", "style": "foot",
                       "text": f"※ 1인당 약 {won(round(total / count))}원 (참석 {count}명 기준). "
                               "1인당 한도는 공사 기준이 확인되지 않아 참고로만 적습니다."})
    blocks.append({"type": "photos", "title": "회의 사진", "hint": "회의 장면 사진을 인쇄본에 붙여 주세요 (식당 사진 불가)"})
    return [{"title": "회 의 록", "blocks": blocks}]


# ---------------------------------------------------------------------------
# 출장보고서
# ---------------------------------------------------------------------------
def trip_destination(sub: dict) -> str:
    """정산 건에 실제 지명이 있으면 그것. 지역 구분(서울/광역시/기타)만 있으면 빈 값."""
    trip = sub.get("trip") or {}
    dest = str(trip.get("destination") or "").strip()
    return "" if dest in _REGION_GROUPS else dest


def _trip_report(sub: dict, fields: dict) -> list[dict]:
    trip = sub.get("trip") or {}
    dates = sorted(str(e.get("date")) for e in _expenses(sub) if e.get("date"))
    start = trip.get("start_date") or (dates[0] if dates else None)
    end = trip.get("end_date") or (dates[-1] if dates else None)

    def remark(e: dict) -> str:
        parts = [str(e["seat_class"])] if e.get("seat_class") else []
        if e.get("nights"):
            parts.append(f"{e['nights']}박")
        return ", ".join(parts)

    return [{"title": "출 장 보 고 서", "approval": APPROVAL, "blocks": [
        {"type": "info", "rows": [
            {"label": "목적", "cell": _cell(sub.get("purpose"))},
            {"label": "출장일자", "cell": _cell(_period(start, end))},
            {"label": "출장지", "cell": _edit(fields, "destination", "출장지", required=True,
                                           placeholder="예: 부산 강서구 부산항 신항")},
        ]},
        _roster("출장명단", [(str(sub.get("dept") or ""), str(sub.get("submitter") or ""))]),
        {"type": "field", "label": "출장 내용", "cell": _edit(
            fields, "content", "출장 내용", required=True, multiline=True, limit=2000,
            placeholder="출장에서 한 일을 메모처럼 편하게 적어 주세요. 적은 뒤 ‘AI로 문장 다듬기’를 누르면 보고서 문체로 정리해 드려요.")},
        _amount_table(sub, str(sub.get("submitter") or ""), 1, remark),
        _evidence(sub, "관련 사진 (집행금액 증빙)"),
    ]}]


# ---------------------------------------------------------------------------
# 공통
# ---------------------------------------------------------------------------
def initial_fields(kind: str, sub: dict, given: dict | None = None) -> dict:
    """정산 건에서 서류를 처음 만들 때 넣어 두는 값. 금액·날짜는 저장하지 않습니다."""
    given = given or {}
    if kind == KIND:
        base = suggest(sub)
        return {**base, "ai_keys": list(base)}
    if kind == MINUTES:
        return {"content": str(given.get("content") or given.get("notes") or "")}
    return {
        "destination": str(given.get("destination") or trip_destination(sub)),
        "content": str(given.get("content") or given.get("work_notes") or ""),
    }


def build(kind: str, sub: dict, fields: dict, writer: str, today: date | None = None) -> dict:
    """제출 건 + 직원 입력값 → 화면이 그대로 그리는 양식."""
    today = today or date.today()
    if kind == KIND:
        sheets = _report(sub, fields, writer, today)
    elif kind == MINUTES:
        sheets = _minutes(sub, fields)
    elif kind == TRIP_REPORT:
        sheets = _trip_report(sub, fields)
    else:
        raise ValueError(f"양식이 없는 서류 종류: {kind}")
    todo = [
        {"key": c["key"], "label": c["label"], "sheet": sheet["title"]}
        for sheet in sheets
        for c in cells(sheet)
        if c.get("key") and c["required"] and not c["value"]
    ]
    return {"kind": kind, "submission_code": sub.get("id"), "sheets": sheets, "todo": todo, "ready": not todo}


def cells(sheet: dict) -> list[dict]:
    """한 장 안의 모든 칸 (위에서 아래 순서)."""
    out: list[dict] = []
    for b in sheet["blocks"]:
        if b["type"] in ("info", "signers"):
            out += [r["cell"] for r in b["rows"]]
        elif b["type"] == "table":
            out += [c for row in b["rows"] for c in row]
        elif b["type"] == "field":
            out.append(b["cell"])
    return out


def default_title(kind: str, sub: dict) -> str:
    name = "지출 결과서" if kind == KIND else kind
    return f"{name} · {sub.get('purpose') or sub.get('id') or ''}"[:100]
