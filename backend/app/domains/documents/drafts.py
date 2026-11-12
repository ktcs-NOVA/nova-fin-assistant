"""서류 초안 만들기 (표준 라이브러리만 사용 — 단위 테스트가 DB·API 키 없이 돕니다).

원칙: AI 는 직원이 직접 적은 메모(수행 내용·논의 내용)를 문장으로 다듬기만 합니다.
날짜·장소·금액·참석자·1인당 금액은 입력값으로 코드가 계산해 채우므로, 지어내지 않습니다.
`polish` 는 메모 문자열 → 다듬은 문자열 함수이고, 기본값은 그대로 돌려주는 함수입니다.
"""

from collections.abc import Callable
from datetime import date

KINDS = ("출장보고서", "회의록", "출장원")

# 초안을 만들려면 꼭 필요한 칸 (키 → 화면에 보일 이름)
REQUIRED = {
    "출장보고서": {
        "trip_start": "출장 시작일",
        "trip_end": "출장 종료일",
        "destination": "출장지",
        "purpose": "출장 목적",
        "work_notes": "주요 수행 내용",
    },
    "회의록": {
        "meeting_title": "회의명",
        "meeting_date": "회의 일시",
        "attendees": "참석자",
        "notes": "논의 내용 메모",
    },
    "출장원": {
        "trip_start": "출장 시작일",
        "trip_end": "출장 종료일",
        "destination": "출장지",
        "purpose": "출장 목적",
        "total_amount": "정산 금액",
    },
}

EXPENSE_LINES = (
    ("transport_fee", "교통비"),
    ("lodging_fee", "숙박비"),
    ("daily_fee", "일비"),
    ("meal_fee", "식비"),
)


def missing(kind: str, fields: dict) -> list[str]:
    """초안에 필요한데 비어 있는 칸의 이름 목록."""
    out = []
    for key, label in REQUIRED[kind].items():
        v = fields.get(key)
        empty = (
            v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v)
        )
        if empty or (key == "total_amount" and not _num(v)):
            out.append(label)
    return out


def _num(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def won(n) -> str:
    return f"{_num(n):,}원"


def fmt_date(s) -> str:
    try:
        d = date.fromisoformat(str(s)[:10])
        return f"{d.year}년 {d.month}월 {d.day}일"
    except ValueError:
        return str(s)


def period(start, end) -> str:
    try:
        nights = (date.fromisoformat(str(end)[:10]) - date.fromisoformat(str(start)[:10])).days
    except ValueError:
        return f"{start} ~ {end}"
    span = fmt_date(start) if nights <= 0 else f"{fmt_date(start)} ~ {fmt_date(end)}"
    return f"{span} ({'당일' if nights <= 0 else f'{nights}박 {nights + 1}일'})"


def per_person(amount, headcount: int) -> int:
    """1인당 금액 (원 단위 반올림)."""
    return int(_num(amount) / headcount + 0.5) if headcount > 0 else 0


def _s(fields: dict, key: str) -> str:
    return str(fields.get(key) or "").strip()


def build(kind: str, fields: dict, who: str, polish: Callable[[str], str] = lambda t: t) -> str:
    """종류별 초안 본문. who 는 '이름 (부서)'."""
    if kind == "출장보고서":
        lines = [
            "국내출장 결과 보고서",
            "",
            f"출장자: {who}",
            f"출장 기간: {period(fields.get('trip_start'), fields.get('trip_end'))}",
            f"출장지: {_s(fields, 'destination')}",
            f"출장 목적: {_s(fields, 'purpose')}",
            "",
            "수행 내용",
            polish(_s(fields, "work_notes")),
        ]
        costs = [
            (label, _num(fields.get(k))) for k, label in EXPENSE_LINES if _num(fields.get(k)) > 0
        ]
        if costs:
            lines += ["", "경비 내역"] + [f"{label}: {won(v)}" for label, v in costs]
            lines.append(f"합계: {won(sum(v for _, v in costs))}")
        return "\n".join(lines)

    if kind == "회의록":
        people = [str(a).strip() for a in fields.get("attendees", []) if str(a).strip()]
        lines = [
            "회의록",
            "",
            f"회의명: {_s(fields, 'meeting_title')}",
            f"일시: {fmt_date(fields.get('meeting_date'))}",
        ]
        if _s(fields, "place"):
            lines.append(f"장소: {_s(fields, 'place')}")
        lines.append(f"참석자: {len(people)}명 ({', '.join(people)})")
        amount = _num(fields.get("receipt_amount"))
        if amount > 0:
            each = won(per_person(amount, len(people)))
            lines.append(f"회의 비용: {won(amount)} · 1인당 {each} (원 미만 반올림)")
        lines += ["", "논의 내용", polish(_s(fields, "notes")), "", f"작성자: {who}"]
        return "\n".join(lines)

    if kind == "출장원":
        return "\n".join(
            [
                "출장원 (정산)",
                "",
                f"출장자: {who}",
                f"출장 기간: {period(fields.get('trip_start'), fields.get('trip_end'))}",
                f"출장지: {_s(fields, 'destination')}",
                f"출장 목적: {_s(fields, 'purpose')}",
                f"정산 금액: {won(fields.get('total_amount'))}",
                "",
                f"서명: {_s(fields, 'signer_name') or '(서명 전)'}",
            ]
        )
    raise ValueError(f"알 수 없는 서류 종류: {kind}")


def default_title(kind: str, fields: dict) -> str:
    detail = _s(fields, "destination") or _s(fields, "meeting_title")
    return f"{kind} · {detail}" if detail else kind
