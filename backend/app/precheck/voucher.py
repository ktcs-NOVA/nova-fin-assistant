"""
U-07 정산 서류 자동 작성 — 지출결의서 초안 · 적요 · 계정과목 제안 · 첨부서류 목록

U-04 와 같은 요청(청구 내역)을 받아, 담당자에게 올릴 지출결의서 초안을 만듭니다.

    from precheck import draft_voucher
    draft = draft_voucher(request_json)

- 건명·적요: 회계규정 시행세칙 제7조 제1호 나목("적요란에 지출건명, 산출내역 … 명기")에 맞춰 작성
- 계정과목: 규정에 이름이 나오는 예산과목(여비교통비·업무추진비·조직관리비)은 "규정 확인",
            나머지는 일반적인 공공기관 비용 과목으로 "가정" 표시
            (KOBC 실제 계정과목 코드표는 공개되어 있지 않음)
- 첨부서류: 회계규정 시행세칙 제8조, 여비규정, 법인카드 지침 기준
- U-04 사전검증을 같이 돌려서 "보완 필요"가 남아 있으면 제출 전 경고를 붙임
- 결의서는 초안일 뿐, 결재는 위임전결규정 시행세칙에 따른 결재권자가 함
"""

from __future__ import annotations

from datetime import date

from . import rules as R
from .engine import _normalize_item, _parse_date, _parse_hour, _text, _won, classify, verify_claim

# ---------------------------------------------------------------------------
# 계정과목(예산과목) 제안 규칙
# ---------------------------------------------------------------------------
CONFIRMED = "규정 확인"
ASSUMED = "가정"

# 카테고리 → (과목, 세목, 확인 수준, 근거)
CATEGORY_ACCOUNTS = {
    "lodging": ("여비교통비", "국내여비(숙박비)", CONFIRMED, "예산세칙 제22조 제2항, 여비규정 제2조"),
    "meal": ("여비교통비", "국내여비(식비)", CONFIRMED, "예산세칙 제22조 제2항, 여비규정 제2조"),
    "per_diem": ("여비교통비", "국내여비(일비)", CONFIRMED, "예산세칙 제22조 제2항, 여비규정 제2조"),
    "transport": ("여비교통비", "국내여비(교통비)", CONFIRMED, "예산세칙 제22조 제2항, 여비규정 제2조"),
    "business": ("업무추진비", "대외 업무협의·간담회", CONFIRMED, "업무추진비 및 조직관리비 집행 지침 제2조 제1항"),
    "condolence": ("업무추진비", "경조사비(경조금)", CONFIRMED, "업무추진비 및 조직관리비 집행 지침 제2조 제1항"),
    "wreath": ("업무추진비", "경조사비(화환)", CONFIRMED, "업무추진비 및 조직관리비 집행 지침 제2조 제1항"),
    "org": ("조직관리비", "부서운영비(회의·다과·회식)", CONFIRMED, "업무추진비 및 조직관리비 집행 지침 제2조 제2항"),
}

# 위에 해당하지 않는 일반 경비: 키워드 → 과목 (가정)
GENERAL_ACCOUNTS = [
    (("문구", "사무용품", "소모품", "토너", "용지"), "소모품비"),
    (("도서", "인쇄", "제본", "출력"), "도서인쇄비"),
    (("통신", "우편", "택배", "등기"), "통신비"),
    (("교육", "세미나", "수강", "연수"), "교육훈련비"),
    (("수수료", "등록비", "발급"), "지급수수료"),
    (("정비", "세차", "차량"), "차량유지비"),
]


def suggest_account(item: dict, is_travel: bool) -> dict:
    cat = classify(item)
    if cat == "meal" and not is_travel:
        cat = "org"  # 출장이 아닌 식사는 회의·회식으로 봄
    if cat in CATEGORY_ACCOUNTS:
        acc, sub, level, basis = CATEGORY_ACCOUNTS[cat]
        return {"account": acc, "sub_account": sub, "confidence": level, "basis": basis}
    t = _text(item)
    for words, acc in GENERAL_ACCOUNTS:
        if any(w in t for w in words):
            return {"account": acc, "sub_account": "", "confidence": ASSUMED,
                    "basis": "KOBC 계정과목표 미공개 — 일반 공공기관 비용 과목으로 가정"}
    return {"account": "담당자 확인", "sub_account": "", "confidence": ASSUMED,
            "basis": "항목명만으로 과목을 정할 수 없음 — 회계책임자 확인 필요 (회계규정 시행세칙 제6조 제3항)"}


# ---------------------------------------------------------------------------
# 적요
# ---------------------------------------------------------------------------
def _item_detail(item: dict, days: int | None) -> str:
    """항목 한 줄 산출내역."""
    cat = classify(item)
    amt = _won(item["amount"])
    if cat == "lodging" and item.get("nights"):
        return f"{amt}({item['nights']}박" + (", 조식 포함)" if item.get("breakfast_included") else ")")
    if cat in {"meal", "per_diem"} and (item.get("days") or days):
        return f"{amt}({item.get('days') or days}일)"
    if item.get("seat_class"):
        return f"{amt}({item['seat_class']})"
    if item.get("merchant"):
        return f"{amt}({item['merchant']})"
    return amt


def _title(req, ctx_dates, region_label, items):
    if req.get("title"):
        return str(req["title"])
    trip_type = str(req.get("trip_type") or "국내출장")
    start, end = ctx_dates
    if "출장" in trip_type:
        where = f"{region_label} " if region_label else ""
        when = ""
        if start:
            when = f"({start.isoformat()}" + (f"~{end.isoformat()})" if end and end != start else ")")
        return f"{where}{trip_type.replace('국내출장', '출장')} 여비 정산{when}".strip()
    first = items[0]
    d = _parse_date(first.get("date"))
    when = f"({d.isoformat()})" if d else ""
    names = ", ".join(dict.fromkeys(i.get("field", "") for i in items))
    return f"{names} 지출{when}"


# ---------------------------------------------------------------------------
# 첨부서류
# ---------------------------------------------------------------------------
def _attachments(req, items, is_travel):
    docs = []

    def add(name, basis, why=""):
        if not any(d["name"] == name for d in docs):
            docs.append({"name": name, "basis": basis, "reason": why})

    if is_travel:
        add("출장원(정산) — 여비규정 별지 제3호", "회계규정 시행세칙 제8조 제2항", "출장비 정산")
        add("출장보고서 — 여비규정 별지 제4호", "회계규정 시행세칙 제8조 제2항", "출장비 정산")
    cats = {classify(i) for i in items}
    if "lodging" in cats:
        add("숙박시설 청구서 + 신용카드영수증", "여비규정 제11조 제1항·제2항",
            "상호·투숙자·호실·기간·요금 내역이 있어야 함")
    if "transport" in cats:
        add("교통비 영수증(승차권·탑승권 포함)", "여비규정 제10조 제1항·제2항")
    if any("법인" in str(i.get("payment") or "") for i in items):
        add("법인카드 사용내역 — 법인카드 지침 별지 제6호", "회계규정 시행세칙 제8조 제3항, 법인카드 지침 제8조 제3항")
    if any("개인" in str(i.get("payment") or "") for i in items):
        add("사유서 — 법인카드 지침 별지 제5호", "법인카드 지침 제7조 제6항", "개인카드 사용분 청구")
    for i in items:
        h = _parse_hour(i.get("time"))
        d = _parse_date(i.get("date"))
        odd = h is not None and (h >= R.ODD_HOURS_START or h < R.ODD_HOURS_END)
        holiday = d is not None and not is_travel and (d.weekday() >= 5 or d.isoformat() in R.HOLIDAYS_2026)
        if "법인" in str(i.get("payment") or "") and (odd or holiday):
            add("사유서 — 법인카드 지침 별지 제5호", "법인카드 지침 제10조 제4항",
                "심야(23~06시) 또는 공휴일·휴무일 사용")
    biz = [i for i in items if classify(i) == "business"]
    if biz:
        add("참석자 명단(상대방 소속·직책·성명, 총인원)", "업무추진비 및 조직관리비 집행 지침 제8조 제1항")
    if any(i["amount"] >= R.BIZ_PRE_APPROVAL for i in biz):
        add("업무추진비 사전결재 문서 — 업무추진비 지침 별지 제1호", "업무추진비 및 조직관리비 집행 지침 제3조 제4항",
            "건당 50만원 이상")
    if any(i["amount"] >= R.BIZ_DAILY_AUDIT for i in biz):
        add("일상감사 결과", "업무추진비 및 조직관리비 집행 지침 제3조 제4항", "건당 100만원 이상")
    if any(classify(i) == "condolence" and "현금" in str(i.get("payment") or "") for i in items):
        add("경조 사실·업무 관련성 증빙", "업무추진비 및 조직관리비 집행 지침 제4조 제1항", "경조금 현금 지출")
    if req.get("tax_invoice"):
        add("(세금)계산서 또는 거래명세", "회계규정 시행세칙 제8조 제1항 제2호")
    if _transit_without_receipt(items):
        add("증빙 대체 결재문서(사유서 · 부서장 승인)", R.SUBSTITUTE_BASIS,
            "철도·버스 영수증을 받기 어려운 구간 — 대중교통 인가요금 기준")
    return docs


# ---------------------------------------------------------------------------
# 철도·버스 증빙 곤란 사유서 템플릿 (결재문서 초안)
# ---------------------------------------------------------------------------
def _transit_without_receipt(items):
    return [i for i in items
            if i.get("receipt") is False and classify(i) == "transport"
            and any(w in _text(i) for w in R.PUBLIC_TRANSIT_WORDS)]


def _mode_label(item):
    seat = item.get("seat_class")
    name = str(item.get("field") or "")
    return f"{name} ({seat})" if seat else name


def _field(key, label, value="", placeholder="", required=True):
    """화면은 value 가 비어 있으면 placeholder 를 흐린 글씨 예시로 보여줍니다."""
    return {"key": key, "label": label, "value": value, "placeholder": placeholder, "required": required}


def _reason_forms(req, items, trip, title):
    forms = []
    requester = dict(req.get("requester") or {})
    period = ""
    if trip.get("start_date"):
        period = str(trip["start_date"])
        if trip.get("end_date") and trip["end_date"] != trip["start_date"]:
            period += f" ~ {trip['end_date']}"
    for it in _transit_without_receipt(items):
        fare = it.get("authorized_fare")
        forms.append({
            "document": "교통비 증빙 대체 사유서",
            "for_item": it.get("field", "교통비"),
            "status": "부서장 승인 완료" if it.get("substitute_approved") is True else "작성 필요",
            "fields": [
                _field("title", "건명", f"{title} — 교통비 증빙 대체 사유서" if title else ""),
                _field("requester", "작성자", " / ".join(x for x in (requester.get("department"),
                                                                 requester.get("name")) if x),
                       "예: 해운정책팀 / 홍길동"),
                _field("period", "출장 기간", period, "예: 2026-10-20 ~ 2026-10-21"),
                _field("route", "이용 구간", str(it.get("route") or ""), "예: 서울역 → 부산역 (편도)"),
                _field("mode", "이용 수단", _mode_label(it), "예: KTX 일반실"),
                _field("amount", "청구 금액", _won(it["amount"]) if it.get("amount") else "", "예: 59,800원"),
                _field("authorized_fare", "인가요금 기준", _won(fare) if fare is not None else "",
                       "예: 코레일 KTX 일반실 서울–부산 59,800원 (출장일 기준 운임표)"),
                _field("reason", "증빙이 어려운 사유", str(it.get("no_receipt_reason") or ""),
                       "예: 역 현장에서 현금으로 발권했고 승차권을 분실해 결제 내역을 조회할 수 없음"),
                _field("approver", "부서장 승인", "", "부서장 결재 후 이 문서를 결의서에 첨부", required=True),
            ],
            "guide": [
                "청구 금액은 같은 구간 대중교통 인가요금을 넘을 수 없습니다.",
                "사유에는 언제·어디서·왜 영수증을 받을 수 없었는지 구체적으로 적습니다.",
                "부서장 승인을 받은 결재문서가 영수증을 대신합니다.",
            ],
            "basis": R.SUBSTITUTE_BASIS,
        })
    return forms


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def draft_voucher(req: dict, today: date | None = None) -> dict:
    items = [_normalize_item(i) for i in (req.get("items") or [])]
    if not items:
        raise ValueError("items가 비어 있습니다.")

    trip = dict(req.get("trip") or {})
    trip_type = str(req.get("trip_type") or "국내출장")
    is_travel = "출장" in trip_type
    start, end = _parse_date(trip.get("start_date")), _parse_date(trip.get("end_date"))
    days = (end - start).days + 1 if start and end and end >= start else None
    region_label = str(trip.get("region") or "")

    # 사전검증 (U-04) — 이미 결과가 있으면 그대로 사용
    check = req.get("verify_result") or verify_claim(req)
    fix_items = [r for r in check["items"] if r["verdict"] == R.FIX]
    review_items = [r for r in check["items"] if r["verdict"] == R.CHECK]

    title = _title(req, (start, end), region_label, items)

    # 과목별로 묶어서 결의서 행 만들기
    lines, by_account = [], {}
    for it in items:
        acc = suggest_account(it, is_travel)
        key = (acc["account"], acc["sub_account"])
        row = by_account.get(key)
        if row is None:
            row = {**acc, "amount": 0, "details": []}
            by_account[key] = row
            lines.append(row)
        row["amount"] += it["amount"]
        row["details"].append(f"{it.get('field', '')} {_item_detail(it, days)}")
    for row in lines:
        row["summary"] = f"{title} — " + ", ".join(row.pop("details"))

    total = sum(i["amount"] for i in items)
    breakdown = ", ".join(f"{i.get('field', '')} {_item_detail(i, days)}" for i in items)
    payments = sorted({str(i.get("payment")) for i in items if i.get("payment")})
    merchants = list(dict.fromkeys(i["merchant"] for i in items if i.get("merchant")))
    requester = dict(req.get("requester") or {})

    warnings = []
    if fix_items:
        warnings.append(f"'보완 필요' {len(fix_items)}건이 남아 있습니다. 수정한 뒤 제출하세요: "
                        + ", ".join(f"{r['field']}({r['basis']})" for r in fix_items))
    if review_items:
        warnings.append(f"'담당자 확인 필요' {len(review_items)}건은 결의서에 표시된 채로 담당자 검토로 넘어갑니다.")
    if any(l["confidence"] == ASSUMED for l in lines):
        warnings.append("일부 계정과목은 가정값입니다. 회계책임자와 확인하세요 (회계규정 시행세칙 제6조 제3항).")

    # 제출 기한 안내
    deadlines = []
    if is_travel and end:
        deadlines.append({"what": "출장비 정산", "due": date.fromordinal(end.toordinal() + R.SETTLEMENT_DAYS).isoformat(),
                          "basis": "여비규정 제3조의2 제2항 (출장 완료일로부터 15일)"})
    card_dates = [_parse_date(i.get("date")) for i in items if "법인" in str(i.get("payment") or "")]
    card_dates = [d for d in card_dates if d]
    if card_dates and not is_travel:
        first = min(card_dates)
        deadlines.append({"what": "법인카드 지출결의", "due": date.fromordinal(first.toordinal() + R.CARD_SETTLEMENT_DAYS).isoformat(),
                          "basis": "법인카드 지침 제8조 제1항 (사용 후 10일)"})

    return {
        "document": "지출결의서(초안)",
        "status": "제출 전 보완 필요" if fix_items else "제출 가능",
        "header": {
            "title": title,
            "requester": requester.get("name", ""),
            "department": requester.get("department", ""),
            "written_on": (today or date.today()).isoformat(),
            "payee": ", ".join(merchants) if merchants else (requester.get("name", "") if is_travel else ""),
            "payment_method": ", ".join(payments) if payments else ("여비 지급" if is_travel else ""),
            "total": total,
        },
        "summary": f"{title}: {breakdown} / 합계 {_won(total)}",
        "lines": lines,
        "attachments": _attachments(req, items, is_travel),
        "reason_forms": _reason_forms(req, items, trip, title),   # 철도·버스 증빙 곤란 시 사유서
        "deadlines": deadlines,
        "verify": {"overall": check["overall"], "fix": len(fix_items), "review": len(review_items)},
        "warnings": warnings,
        "approval_note": "이 결의서는 AI가 만든 초안입니다. 결재는 위임전결규정 시행세칙에 따른 결재권자가 합니다 "
                         "(회계규정 시행세칙 제11조).",
    }

