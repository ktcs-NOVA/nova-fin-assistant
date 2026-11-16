"""기본 양식: 지출 결과서 + 검수확인서 (표준 라이브러리만 사용 — 단위 테스트가 DB·API 키 없이 돕니다).

양식의 칸 구성은 여기 한 곳에서 정합니다. 칸마다 값이 어디서 오는지(source)를 붙여서
화면이 색으로 구분하고, 직원이 직접 적어야 하는 칸만 골라 안내할 수 있게 합니다.

  auto    정산 건에서 그대로 가져온 값 (금액·날짜·건명 …). 서류에서 고칠 수 없음
  ai      AI 가 제안한 문구 (상세내역·용도). 직원이 고칠 수 있음
  manual  직원이 직접 적는 칸 (검수자, 특이 사항)
  blank   시스템 밖에서 채우는 칸 (서명·날인, 회계 담당 확인)

`sub` 는 submissions.service.to_view() 가 돌려주는 제출 건 한 건(dict), `fields` 는 서류에 저장된
직원 입력값({"detail_0": …, "use_0": …, "inspector": …, "remark": …, "ai_keys": [...]}) 입니다.
금액·날짜는 항상 sub 에서 다시 읽으므로 서류에서 숫자가 달라질 수 없습니다.
"""

from datetime import date

KIND = "지출결과서"
ORG = "한국해양진흥공사"

AUTO, AI, MANUAL, BLANK = "auto", "ai", "manual", "blank"


def expected_kinds(sub_type: str) -> list[str]:
    """정산 유형별로 함께 내야 하는 서류 (관리자 화면의 '받은 서류 / 아직 안 온 서류' 기준)."""
    if "출장" in (sub_type or ""):
        return [KIND, "출장보고서", "출장원"]
    if sub_type == "회의비":
        return [KIND, "회의록"]
    return [KIND]


def won(n) -> str:
    return f"{int(n or 0):,}"


def short_date(s) -> str:
    """'2026-11-12' → '26.11.12' (원 양식의 지출날짜 표기)."""
    try:
        d = date.fromisoformat(str(s)[:10])
    except ValueError:
        return str(s or "")
    return f"{d.year % 100:02d}.{d.month:02d}.{d.day:02d}"


def long_date(d: date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일"


def _expenses(sub: dict) -> list[dict]:
    return list(sub.get("expenses") or [])


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


def suggest(sub: dict) -> dict[str, str]:
    """AI 칸(상세내역·용도)의 기본 제안. 정산 건에 있는 사실만 조합하고, 없는 내용은 만들지 않습니다."""
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


def ai_keys(sub: dict) -> list[str]:
    return list(suggest(sub).keys())


def _cell(value="", source=AUTO, key=None, required=False, placeholder="", align=None) -> dict:
    cell = {"value": "" if value is None else str(value), "source": source}
    if key:
        cell["key"] = key
        cell["label"] = _todo_label(key)  # 안내 문구용 이름 (예: 1번 상세내역)
        cell["required"] = required
        if placeholder:
            cell["placeholder"] = placeholder
    if align:
        cell["align"] = align
    return cell


def _edit(fields: dict, key: str, required: bool, placeholder: str = "", manual: bool = False) -> dict:
    """고칠 수 있는 칸. 값이 AI 제안 그대로면 ai, 직원이 적었으면(또는 원래 직접 적는 칸이면) manual."""
    value = str(fields.get(key) or "").strip()
    from_ai = not manual and (not value or key in (fields.get("ai_keys") or []))
    return _cell(value, AI if from_ai else MANUAL, key, required, placeholder)


def build(sub: dict, fields: dict, writer: str, today: date | None = None) -> dict:
    """제출 건 + 직원 입력값 → 화면이 그대로 그리는 양식 두 장(지출 결과서, 검수확인서)."""
    today = today or date.today()
    rows = _expenses(sub)
    total = sum(int(e.get("amount") or 0) for e in rows)
    category = str(sub.get("account") or sub.get("type") or "")

    report_rows, check_rows, evidence = [], [], []
    for i, e in enumerate(rows):
        amount = int(e.get("amount") or 0)
        qty = _qty(e)
        report_rows.append([
            _cell(i + 1, align="center"),
            _cell(_item_name(e)),
            _edit(fields, f"detail_{i}", True, "예: 외부 기관 업무협의 식대 (4인)"),
            _cell(short_date(e.get("date")), align="center"),
            _cell(f"{won(amount)}원", align="right"),
        ])
        check_rows.append([
            _cell(i + 1, align="center"),
            _cell(category, align="center"),
            _cell(_item_name(e)),
            _edit(fields, f"use_{i}", True, "예: 업무협의 식대"),
            _cell(qty, align="center"),
            _cell(won(amount // qty), align="right"),
            _cell(won(amount), align="right"),
        ])
        evidence.append({
            "date": short_date(e.get("date")),
            "label": f"{category} / {_item_name(e)}",
            "amount": f"{won(amount)}원",
            "payment": str(e.get("payment") or ""),
            "receipt_id": e.get("receipt_id"),
        })

    sheets = [
        {
            "title": "지출 결과서",
            "info": [
                {"label": "기관명", "cell": _cell(ORG)},
                {"label": "건명", "cell": _cell(sub.get("purpose"))},
                {"label": "부서", "cell": _cell(sub.get("dept"))},
                {"label": "정산 유형 · 제출 번호", "cell": _cell(f"{sub.get('type') or ''} · {sub.get('id') or ''}")},
            ],
            "table": {
                "columns": [
                    {"label": "번호", "width": "8%"}, {"label": "내용(품명)", "width": "26%"},
                    {"label": "상세내역", "width": "34%"}, {"label": "지출날짜", "width": "14%"},
                    {"label": "금액", "width": "18%"},
                ],
                "rows": report_rows,
                "total": {"label": "소 계", "value": f"{won(total)} 원"},
            },
            "extra": [{"label": "특이 사항", "cell": _edit(fields, "remark", False, "없으면 비워 두세요", manual=True)}],
            "closing": "위와 같이 지출 결과를 보고합니다.",
            "date": long_date(today),
            "signers": [
                {"role": "작성자", "cell": _cell(writer)},
                {"role": "확인자 (회계 담당)", "cell": _cell("", BLANK)},
            ],
            "footnote": "※ 첨부. 지출 증빙(검수확인서, 회의록, 출장보고서 등)",
        },
        {
            "title": "검수확인서",
            "info": [
                {"label": "건명", "cell": _cell(sub.get("purpose"))},
                {"label": "부서", "cell": _cell(sub.get("dept"))},
            ],
            "table": {
                "columns": [
                    {"label": "순번", "width": "7%"}, {"label": "구분", "width": "14%"},
                    {"label": "품명", "width": "25%"}, {"label": "용도", "width": "24%"},
                    {"label": "수량", "width": "7%"}, {"label": "단가(원)", "width": "11%"},
                    {"label": "금액(원)", "width": "12%"},
                ],
                "rows": check_rows,
                "total": {"label": "합 계", "value": f"{won(total)} 원"},
            },
            "extra": [],
            "closing": "상기와 같이 검사(수)함",
            "date": long_date(today),
            "signers": [
                {"role": "검사(수)자", "cell": _edit(fields, "inspector", True, "예: 총무인사부 부서장 홍길동", manual=True)},
            ],
            "evidence": evidence,
        },
    ]

    todo = []
    for sheet in sheets:
        cells = [c for row in sheet["table"]["rows"] for c in row]
        cells += [x["cell"] for x in sheet["extra"]] + [s["cell"] for s in sheet["signers"]]
        for c in cells:
            if c.get("key") and c.get("required") and not c["value"]:
                todo.append({"key": c["key"], "label": _todo_label(c["key"]), "sheet": sheet["title"]})

    return {
        "kind": KIND,
        "submission_code": sub.get("id"),
        "sheets": sheets,
        "todo": todo,
        "ready": not todo,
    }


def _todo_label(key: str) -> str:
    if key == "inspector":
        return "검사(수)자 소속·성명"
    if key == "remark":
        return "특이 사항"
    name, _, idx = key.partition("_")
    label = {"detail": "상세내역", "use": "용도"}.get(name, name)
    return f"{int(idx) + 1}번 {label}" if idx.isdigit() else label


def default_title(sub: dict) -> str:
    return f"지출 결과서 · {sub.get('purpose') or sub.get('id') or ''}"[:100]
