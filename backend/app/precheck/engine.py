"""
U-04 지출 사전검증 엔진 (규칙 기반)

docs/API.md 의 `POST /api/verify` 요청 JSON을 받아 응답 JSON을 돌려줍니다.
백엔드 서버는 이 함수만 호출하면 됩니다.

    from app.precheck import verify_claim
    result = verify_claim(request_json)

입력 형태는 API.md 와 같고, 아래 필드는 "있으면 더 정확하게 검사하는" 선택 필드입니다.
없으면 해당 규칙은 건너뛰거나 "담당자 확인 필요"로 안내합니다.
자세한 필드 설명은 README.md 참고.

판정 원칙
- 규정에 숫자·조건이 명확한 위반          -> 보완 필요
- 규정상 예외가 가능해서 사람이 판단해야 함 -> 담당자 확인 필요
- 걸린 규칙이 없음                        -> 규정상 확인 가능
- 최종 승인/반려는 항상 담당자가 한다 (이 엔진은 제출 전 사전검증만 함)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from . import rules as R


# ---------------------------------------------------------------------------
# 작은 도우미 함수들
# ---------------------------------------------------------------------------
def _won(n: float) -> str:
    return f"{int(round(n)):,}원"


def _parse_date(s):
    if not s:
        return None
    if isinstance(s, date):
        return s
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_hour(s):
    """'23:30' -> 23. 형식이 다르면 None."""
    if s is None or s == "":
        return None
    try:
        return int(str(s).split(":")[0])
    except ValueError:
        return None


def _text(item) -> str:
    """항목명·메모·카테고리를 합친 검색용 문자열."""
    parts = [item.get("field", ""), item.get("category", ""), item.get("note", ""),
             item.get("merchant", ""), item.get("merchant_type", "")]
    return " ".join(str(p) for p in parts if p)


def _normalize_item(item: dict) -> dict:
    """U-06 영수증 화면의 '지출 건 초안' 필드명도 그대로 받기 위한 변환.
    purpose -> field, business_type -> merchant_type, total_amount -> amount
    """
    it = dict(item)
    if not it.get("field") and it.get("purpose"):
        it["field"] = it["purpose"]
    if not it.get("merchant_type") and it.get("business_type"):
        it["merchant_type"] = it["business_type"]
    if "amount" not in it and "total_amount" in it:
        it["amount"] = it["total_amount"]
    it["amount"] = int(it.get("amount") or 0)
    return it


def _has(text: str, *words) -> bool:
    return any(w in text for w in words)


def _finding(item, verdict, message, basis, fix="", rule_id=""):
    return {
        "field": item.get("field", "청구 전체") if isinstance(item, dict) else item,
        "verdict": verdict,
        "message": message,
        "basis": basis,
        "fix": fix,
        "rule_id": rule_id,
    }


# ---------------------------------------------------------------------------
# 입력 정리
# ---------------------------------------------------------------------------
def normalize_grade(grade: str | None) -> str:
    g = (grade or "").replace(" ", "")
    if "사장" in g:
        return R.GRADE_PRESIDENT
    if "감사" in g:
        return R.GRADE_AUDITOR
    if _has(g, "임원", "본부장"):
        return R.GRADE_EXECUTIVE
    if _has(g, "1급", "2급", "1·2급", "1,2급", "부서장"):
        # 별표 1 주3) 3급 부서장은 2급 기준을 적용할 수 있음
        return R.GRADE_STAFF_1_2
    return R.GRADE_STAFF_3  # 기본값: 가장 많은 직원 등급


def classify(item) -> str:
    """항목을 검사 유형으로 분류."""
    if item.get("category") in {"lodging", "meal", "per_diem", "transport",
                                "business", "org", "condolence", "wreath", "general"}:
        return item["category"]
    # 항목명(field)을 먼저 보고, 거기서 못 정하면 메모까지 본다.
    # (예: 항목명 "식비", 메모 "조식 포함 숙박" -> 숙박비가 아니라 식비)
    by_field = _classify_text(f"{item.get('field', '')} {item.get('category', '')}")
    return by_field if by_field != "general" else _classify_text(_text(item))


def _classify_text(t: str) -> str:
    if "숙박" in t:
        return "lodging"
    if "일비" in t:
        return "per_diem"
    if "화환" in t:
        return "wreath"
    if "경조" in t:
        return "condolence"
    if _has(t, "업무추진비", "간담회", "접대", "유관기관"):
        return "business"
    if _has(t, "조직관리비", "부서운영비", "회식", "다과", "회의"):
        return "org"
    if "식비" in t:
        return "meal"
    if _has(t, "교통", "운임", "철도", "KTX", "SRT", "항공", "버스", "선박",
            "유류", "주유", "자가용", "자차", "통행료", "주차", "택시"):
        return "transport"
    return "general"


def _trip_context(req):
    trip = dict(req.get("trip") or {})
    for k in ("start_date", "end_date", "region", "vehicle", "private_car_approved",
              "settlement_date", "hours", "round_trip_km"):
        if k not in trip and k in req:
            trip[k] = req[k]

    start, end = _parse_date(trip.get("start_date")), _parse_date(trip.get("end_date"))
    days = (end - start).days + 1 if start and end and end >= start else None
    region = R.REGION_ALIASES.get(str(trip.get("region", "")).strip(), None)
    vehicle = str(trip.get("vehicle") or "").replace(" ", "")
    trip_type = str(req.get("trip_type") or "국내출장").replace(" ", "")

    return {
        "start": start, "end": end, "days": days,
        "region": region, "vehicle": vehicle,
        "company_car": vehicle in {v.replace(" ", "") for v in R.COMPANY_VEHICLES},
        "private_car": vehicle in R.PRIVATE_CAR,
        "private_car_approved": trip.get("private_car_approved"),
        "settlement": _parse_date(trip.get("settlement_date") or req.get("settlement_date")),
        "hours": trip.get("hours"),
        "round_trip_km": trip.get("round_trip_km"),
        "is_travel": "출장" in trip_type,
        "is_intra_city": "근무지내" in trip_type,
    }


# ---------------------------------------------------------------------------
# 여비규정 검사
# ---------------------------------------------------------------------------
def _check_lodging(item, grade, ctx):
    out = []
    row = R.DOMESTIC_TABLE[grade]
    nights = int(item.get("nights") or (ctx["days"] - 1 if ctx["days"] and ctx["days"] > 1 else 1))
    amount = item.get("amount", 0)

    if item.get("receipt") is False:
        out.append(_finding(item, R.FIX,
                            "숙박비 실비 정산에는 숙박시설 청구서와 신용카드영수증이 필요합니다.",
                            "여비규정 제11조 제1항", "숙박시설 발행 청구서와 카드영수증 첨부",
                            "T-LODGING-RECEIPT"))

    if row["lodging"] is None:  # 임원급: 실비
        return out
    if not ctx["region"]:
        out.append(_finding(item, R.CHECK,
                            "출장지(서울/광역시/기타)를 알 수 없어 숙박비 상한을 판단하지 못했습니다.",
                            R.BASIS_TABLE1, "출장지 지역 정보 입력", "T-LODGING-REGION"))
        return out

    cap = row["lodging"][ctx["region"]] * nights        # 제14조②: 박수 합계가 총 한도
    extra_cap = cap * (1 + R.LODGING_EXTRA_RATIO)       # 제11조⑥: 30%까지 추가 가능

    if amount <= cap:
        return out
    if amount <= extra_cap:
        out.append(_finding(item, R.CHECK,
                            f"{ctx['region']} 숙박비 상한 {_won(cap)}({nights}박)을 {_won(amount - cap)} 초과했습니다. "
                            f"부득이한 사유가 있으면 상한의 30%({_won(extra_cap)})까지 추가 지급할 수 있습니다.",
                            "여비규정 제11조 제6항, 별표 1",
                            "초과 사유(행사 기간 숙소 부족 등) 소명 후 담당자 판단",
                            "T-LODGING-EXTRA"))
    else:
        out.append(_finding(item, R.FIX,
                            f"{ctx['region']} 숙박비 상한 {_won(cap)}({nights}박)의 30% 추가 한도({_won(extra_cap)})까지 넘었습니다.",
                            "여비규정 제11조 제6항, 별표 1",
                            f"숙박비 청구액을 최대 {_won(extra_cap)} 이내로 수정 (초과분 본인 부담)",
                            "T-LODGING-CAP"))
    return out


def _check_meal(item, grade, ctx, breakfast_nights, provided_meals):
    out = []
    daily = R.DOMESTIC_TABLE[grade]["meal"]
    days = int(item.get("days") or ctx["days"] or 1)
    amount = item.get("amount", 0)
    limit = daily * days

    note = _text(item)
    b_nights = breakfast_nights
    if item.get("breakfast_included") or ("조식" in note and "미포함" not in note):
        b_nights = max(b_nights, int(item.get("breakfast_count") or 1))
    meals_given = int(item.get("meals_provided") or provided_meals or 0)

    breakfast_deduct = daily * R.BREAKFAST_MEAL_DEDUCT * b_nights
    provided_deduct = daily * R.PROVIDED_MEAL_DEDUCT * meals_given
    allowed = limit - breakfast_deduct - provided_deduct

    if amount <= allowed + 0.5:
        return out

    if amount <= limit and b_nights:
        out.append(_finding(item, R.FIX,
                            f"숙박비에 조식이 포함되어 있어 식비의 1/3({_won(daily / 3)} × {b_nights}회)을 차감해야 합니다.",
                            "여비규정 제11조 제4항",
                            f"식비 청구액을 {_won(amount)}에서 {_won(allowed)}으로 수정",
                            "T-MEAL-BREAKFAST"))
    elif amount <= limit and meals_given:
        out.append(_finding(item, R.FIX,
                            f"주최 측이 식사를 {meals_given}회 무료 제공해 1식당 식비의 1/3을 감액해야 합니다.",
                            "여비규정 제15조 제2항",
                            f"식비 청구액을 {_won(allowed)}으로 수정",
                            "T-MEAL-PROVIDED"))
    else:
        out.append(_finding(item, R.FIX,
                            f"식비는 1일 {_won(daily)} × {days}일 = {_won(limit)}이 한도인데 {_won(amount)}을 청구했습니다.",
                            "여비규정 제14조 제1항, 별표 1",
                            f"식비 청구액을 {_won(allowed)} 이내로 수정",
                            "T-MEAL-CAP"))
    return out


def _check_per_diem(item, grade, ctx):
    daily = R.DOMESTIC_TABLE[grade]["per_diem"]
    days = int(item.get("days") or ctx["days"] or 1)
    amount = item.get("amount", 0)
    company_car = ctx["company_car"] or _has(_text(item), "업무용", "공용차량", "렌트")
    limit = daily * days * (R.COMPANY_CAR_PER_DIEM_RATIO if company_car else 1)

    if amount <= limit:
        return []
    if company_car:
        return [_finding(item, R.FIX,
                         "업무용·렌트 차량을 이용한 출장은 일비의 1/2만 지급됩니다.",
                         "여비규정 제14조 제1항",
                         f"일비를 {_won(amount)}에서 {_won(limit)}으로 수정",
                         "T-PERDIEM-CAR")]
    return [_finding(item, R.FIX,
                     f"일비는 1일 {_won(daily)} × {days}일 = {_won(limit)}이 한도입니다.",
                     "여비규정 제14조 제1항, 별표 1",
                     f"일비를 {_won(limit)}으로 수정", "T-PERDIEM-CAP")]


def _check_transport(item, grade, ctx):
    out = []
    t = _text(item)
    amount = item.get("amount", 0)
    is_toll_parking = _has(t, "통행료", "주차")

    if item.get("passenger") or "동승" in t:
        out.append(_finding(item, R.FIX,
                            "같은 목적으로 차량 1대에 동승한 사람에게는 교통비를 지급하지 않습니다.",
                            "여비규정 제13조 제7항", "동승자 교통비 항목 삭제", "T-TRANS-PASSENGER"))

    if ctx["company_car"] and not is_toll_parking and not _has(t, "자가용", "자차"):
        out.append(_finding(item, R.FIX,
                            "업무용 차량을 이용한 구간은 교통비를 지급하지 않습니다. 통행료·주차비만 실비 청구할 수 있습니다.",
                            "여비규정 제13조 제3항",
                            "해당 구간 교통비 삭제 (통행료·주차비는 증빙 첨부 후 별도 청구)",
                            "T-TRANS-COMPANYCAR"))

    private = ctx["private_car"] or _has(t, "자가용", "자차", "유류", "주유")
    if private:
        approved = item.get("private_car_approved", ctx["private_car_approved"])
        if approved is not True:
            out.append(_finding(item, R.CHECK,
                                "자가용 이용은 업무용 차량을 쓸 수 없거나 대중교통이 어려운 경우 등 출장승인권자가 인정할 때만 가능합니다. 승인 여부를 확인해 주세요.",
                                "여비규정 제13조 제5항",
                                "출장 신청서의 자가용 승인 여부 확인 후 첨부",
                                "T-TRANS-PRIVATE-APPROVAL"))
        fare = item.get("public_fare")
        if fare is not None and amount > fare:
            out.append(_finding(item, R.FIX,
                                f"자가용 실비(연료비·통행료 포함)는 같은 구간 철도·버스 운임({_won(fare)})을 넘을 수 없습니다.",
                                "여비규정 제13조 제6항, 별표 1 주2)",
                                f"자가용 교통비를 {_won(fare)}으로 수정",
                                "T-TRANS-PRIVATE-CAP"))

    seat = str(item.get("seat_class") or "")
    rail_grade = R.DOMESTIC_TABLE[grade]["rail"]
    if _has(t, "철도", "KTX", "SRT", "기차") and ("특실" in seat or "특실" in t) and rail_grade == "일반":
        out.append(_finding(item, R.FIX,
                            f"{grade}의 철도운임은 일반실 기준입니다.",
                            R.BASIS_TABLE1,
                            "일반실 운임으로 수정 (차액은 본인 부담)", "T-TRANS-RAIL-CLASS"))
    if "항공" in t and ("비즈니스" in seat or "비즈니스" in t) and R.DOMESTIC_TABLE[grade]["air"] == "이코노미":
        out.append(_finding(item, R.FIX,
                            f"{grade}의 항공운임은 이코노미 기준입니다.",
                            R.BASIS_TABLE1,
                            "이코노미 운임으로 수정 (차액은 본인 부담)", "T-TRANS-AIR-CLASS"))

    if item.get("receipt") is False:
        out.append(_finding(item, R.FIX,
                            "교통비는 사용내역을 확인할 수 있는 영수증(승차권·탑승권 포함)을 제출해야 합니다.",
                            "여비규정 제10조 제1항·제2항", "영수증 또는 승차권 첨부",
                            "T-TRANS-RECEIPT"))
    return out


def _check_intra_city(item, ctx):
    """근무지 내 출장(같은 시·군): 교통비 정액만 지급."""
    cat = classify(item)
    if cat != "transport":
        return [_finding(item, R.FIX,
                         "근무지 내 출장은 교통비만 지급되고 일비·식비·숙박비는 지급되지 않습니다.",
                         "여비규정 제16조 제1항", "해당 항목 삭제", "T-INTRA-ONLY-FARE")]
    if ctx["company_car"]:
        return [_finding(item, R.FIX, "업무용 차량을 이용한 근무지 내 출장은 교통비를 지급하지 않습니다.",
                         "여비규정 제16조 제1항", "교통비 항목 삭제", "T-INTRA-COMPANYCAR")]
    km = ctx["round_trip_km"]
    if km is not None and km < R.INTRA_CITY_MIN_KM:
        return [_finding(item, R.FIX, f"왕복 {R.INTRA_CITY_MIN_KM}km 미만 근무지 내 출장은 교통비를 지급하지 않습니다.",
                         "여비규정 제16조 제1항", "교통비 항목 삭제", "T-INTRA-DISTANCE")]
    hours = ctx["hours"]
    if hours is None:
        return [_finding(item, R.CHECK, "출장시간(4시간 이상/미만)에 따라 정액이 달라집니다. 출장시간을 확인해 주세요.",
                         "여비규정 제16조 제1항", "출장시간 입력", "T-INTRA-HOURS")]
    fare = R.INTRA_CITY_FARE_LONG if float(hours) >= 4 else R.INTRA_CITY_FARE_SHORT
    if item.get("amount", 0) > fare:
        return [_finding(item, R.FIX,
                         f"근무지 내 출장 {'4시간 이상' if fare == R.INTRA_CITY_FARE_LONG else '4시간 미만'}은 교통비 {_won(fare)} 정액입니다.",
                         "여비규정 제16조 제1항", f"교통비를 {_won(fare)}으로 수정", "T-INTRA-FARE")]
    return []


# ---------------------------------------------------------------------------
# 법인카드 지침 검사
# ---------------------------------------------------------------------------
def _is_holiday(d: date) -> bool:
    return d.weekday() >= 5 or d.isoformat() in R.HOLIDAYS_2026


def _check_card(item, ctx):
    out = []
    t = _text(item)
    payment = str(item.get("payment") or "")
    has_reason = bool(item.get("reason_doc")) or "사유서" in t

    # 제10조③ 사용 제한 업종 (사용 자체가 불가)
    for kind, words in R.BANNED_MERCHANTS.items():
        if _has(t, *words):
            out.append(_finding(item, R.FIX,
                                f"법인카드(클린카드) 사용이 제한된 업종({kind})입니다.",
                                "법인카드 관리 및 사용 지침 제10조 제3항",
                                "카드 결제 취소, 취소가 불가능하면 사용금액을 공사 계좌로 반납 (제11조 제3항)",
                                "C-BANNED-MERCHANT"))
            return out  # 사용 불가 업종이면 다른 사유는 의미 없음

    if payment and "법인" not in payment:
        if "개인" in payment:
            out.append(_finding(item, R.FIX if not has_reason else R.CHECK,
                                "개인카드 사용액을 법인비용으로 청구하려면 증빙과 사유서가 필요합니다.",
                                "법인카드 관리 및 사용 지침 제7조 제6항",
                                "영수증과 별지 제5호 사유서를 지출결의서에 첨부",
                                "C-PERSONAL-CARD"))
        return out  # 아래 규칙은 법인카드 사용분에만 해당

    reasons = []
    if _has(t, *R.OTHER_BARS):
        reasons.append(("기타주점업(호프·와인바 등)에서 사용", "제10조 제4항 제4호", "C-OTHER-BAR"))
    hour = _parse_hour(item.get("time"))
    if hour is not None and (hour >= R.ODD_HOURS_START or hour < R.ODD_HOURS_END):
        reasons.append(("비정상시간대(23시~익일 06시)에 사용", "제10조 제4항 제2호", "C-ODD-HOURS"))
    d = _parse_date(item.get("date"))
    if d and _is_holiday(d) and not ctx["is_travel"]:
        reasons.append(("공휴일·휴무일에 사용", "제10조 제4항 제1호", "C-HOLIDAY"))

    for what, art, rid in reasons:
        if has_reason:
            out.append(_finding(item, R.CHECK,
                                f"{what}한 건으로, 사유서가 첨부되어 있습니다. 불가피성(출장·시간외근무·공식행사 등) 판단이 필요합니다.",
                                f"법인카드 관리 및 사용 지침 {art}",
                                "사유서 내용과 객관적 증빙(출장·시간외근무 기록 등) 확인", rid))
        else:
            out.append(_finding(item, R.FIX,
                                f"{what}한 건은 불가피한 사유가 증명될 때만 허용되며 사유서가 필요합니다.",
                                f"법인카드 관리 및 사용 지침 {art}",
                                "별지 제5호 사유서를 작성해 지출결의서에 첨부", rid))

    # 제8조① 카드 사용 후 10일 이내 지출결의 (여비는 여비규정 15일 기준을 따로 봄)
    if not ctx["is_travel"] and d and ctx["settlement"]:
        late = (ctx["settlement"] - d).days
        if late > R.CARD_SETTLEMENT_DAYS:
            out.append(_finding(item, R.CHECK,
                                f"카드 사용 후 {late}일이 지나 지출결의 기한(10일)을 넘겼습니다. 장기출장 등 불가피한 사유면 사유 소멸 후 7일까지 가능합니다.",
                                "법인카드 관리 및 사용 지침 제8조 제1항",
                                "지연 사유 확인 (기한 경과로 생긴 연체료는 사용자 부담)",
                                "C-LATE-SETTLEMENT"))
    return out


# ---------------------------------------------------------------------------
# 업무추진비 지침 검사
# ---------------------------------------------------------------------------
def _check_business(item):
    out = []
    cat = classify(item)
    amount = item.get("amount", 0)
    payment = str(item.get("payment") or "")
    basis = "업무추진비 및 조직관리비 집행 지침"

    if cat == "condolence":
        if amount > R.CONDOLENCE_CASH_LIMIT:
            out.append(_finding(item, R.FIX, f"경조금은 1회 {_won(R.CONDOLENCE_CASH_LIMIT)}을 넘을 수 없습니다.",
                                f"{basis} 제7조", f"경조금을 {_won(R.CONDOLENCE_CASH_LIMIT)} 이내로 수정",
                                "B-CONDOLENCE-CAP"))
        return out  # 경조금은 현금 지출 허용 (제4조① 단서)
    if cat == "wreath":
        if amount > R.CONDOLENCE_WREATH_LIMIT:
            out.append(_finding(item, R.FIX, f"경조 화환은 {_won(R.CONDOLENCE_WREATH_LIMIT)}을 넘을 수 없습니다.",
                                f"{basis} 제7조", f"화환 금액을 {_won(R.CONDOLENCE_WREATH_LIMIT)} 이내로 수정",
                                "B-WREATH-CAP"))
        return out

    if payment and "법인" not in payment:
        out.append(_finding(item, R.FIX, "업무추진비·조직관리비는 반드시 법인카드로 지출해야 합니다.",
                            f"{basis} 제4조 제1항", "법인카드로 재결제하거나 담당자와 처리 방법 협의",
                            "B-CARD-ONLY"))

    if cat == "business":
        if amount >= R.BIZ_PRE_APPROVAL and not item.get("pre_approved"):
            extra = " 100만원 이상이라 일상감사도 받아야 합니다." if amount >= R.BIZ_DAILY_AUDIT else ""
            out.append(_finding(item, R.FIX,
                                f"건당 50만원 이상 업무추진비는 사전에 전사예산관리자의 결재가 필요합니다.{extra}",
                                f"{basis} 제3조 제4항",
                                "별지 제1호 서식 사전결재 문서 첨부" + (" + 일상감사 결과" if extra else ""),
                                "B-PRE-APPROVAL"))
        elif amount >= R.BIZ_DAILY_AUDIT and not item.get("daily_audit"):
            out.append(_finding(item, R.FIX, "100만원 이상 업무추진비는 사전결재 후 일상감사를 받아야 합니다.",
                                f"{basis} 제3조 제4항", "일상감사 결과 첨부", "B-DAILY-AUDIT"))

        if not (item.get("attendees") or item.get("counterpart_info")):
            out.append(_finding(item, R.FIX,
                                "업무추진비는 업무관련성 입증을 위해 사용자, 총인원, 상대방 소속·직책·성명을 제출해야 합니다.",
                                f"{basis} 제8조 제1항",
                                "참석자 명단(상대방 소속·직책·성명, 총인원) 첨부", "B-COUNTERPART"))
    return out


def _check_split_payment(items):
    """제3조⑤: 같은 날·같은 거래처에서 50만원 미만으로 나눠 결제한 업무추진비는 1건으로 본다."""
    groups = defaultdict(list)
    for it in items:
        if classify(it) == "business" and it.get("merchant"):
            groups[(it.get("date"), it["merchant"])].append(it)
    out = []
    for (d, merchant), its in groups.items():
        total = sum(i.get("amount", 0) for i in its)
        if len(its) >= 2 and total >= R.BIZ_PRE_APPROVAL and all(i.get("amount", 0) < R.BIZ_PRE_APPROVAL for i in its):
            if not any(i.get("pre_approved") for i in its):
                out.append(_finding({"field": "업무추진비(분할결제)"}, R.FIX,
                                    f"{d} {merchant}에서 {len(its)}건 합계 {_won(total)}을 나눠 결제했습니다. 1건으로 보아 50만원 이상 기준이 적용됩니다.",
                                    "업무추진비 및 조직관리비 집행 지침 제3조 제5항",
                                    "1건으로 합쳐 별지 제1호 사전결재 문서 첨부", "B-SPLIT-PAYMENT"))
    return out


# ---------------------------------------------------------------------------
# 출장 묶음 검사 (여러 항목을 함께 봐야 잡히는 규칙)
# ---------------------------------------------------------------------------
def _check_trip_bundle(items, ctx, grade):
    out = []
    # 1) 정산 기한
    if ctx["is_travel"] and ctx["end"] and ctx["settlement"]:
        late = (ctx["settlement"] - ctx["end"]).days
        if late > R.SETTLEMENT_DAYS:
            out.append(_finding({"field": "정산 기한"}, R.CHECK,
                                f"출장 종료 후 {late}일이 지나 정산 기한(15일)을 넘겼습니다. 법인카드 매입정보 통보가 늦은 경우에는 통보일로부터 1주일까지 연장됩니다.",
                                "여비규정 제3조의2 제2항", "지연 사유 확인", "T-LATE-SETTLEMENT"))

    # 2) 출장 중 법인카드 식사 + 식비 정액 동시 청구
    #    KOBC 여비규정에 명시 조항은 없어, 제15조②(숙식 무료 제공 시 감액)를 준용한 실무 가정입니다.
    has_meal_allowance = any(classify(i) == "meal" for i in items)
    card_meals = [i for i in items
                  if i.get("card_meal") or (classify(i) in {"general", "org", "business"}
                                            and _has(_text(i), "식사", "식당", "식대")
                                            and "법인" in str(i.get("payment") or "법인"))]
    if ctx["is_travel"] and has_meal_allowance and card_meals:
        if ctx["start"] and ctx["end"]:
            card_meals = [i for i in card_meals
                          if (d := _parse_date(i.get("date"))) and ctx["start"] <= d <= ctx["end"]]
        if card_meals:
            per = R.DOMESTIC_TABLE[grade]["meal"] / 3
            out.append(_finding({"field": "식비(출장 중 법인카드 식사)"}, R.CHECK,
                                f"출장 기간 중 법인카드로 결제한 식사가 {len(card_meals)}건 있는데 식비 정액도 함께 청구했습니다. 중복 지급 여부 확인이 필요합니다.",
                                "여비규정 제15조 제2항 준용 (실무자 의견 기반 가정)",
                                f"법인카드 식사 1회당 식비 1/3({_won(per)}) 차감 여부를 담당자와 확인",
                                "T-MEAL-CARD-DUP"))
    return out


# ---------------------------------------------------------------------------
# 메인 함수
# ---------------------------------------------------------------------------
def verify_claim(req: dict) -> dict:
    """POST /api/verify 요청 -> 응답 (docs/API.md 3-2 형식)."""
    items = [_normalize_item(i) for i in (req.get("items") or [])]
    if not items:
        raise ValueError("items가 비어 있습니다.")

    grade = normalize_grade(req.get("grade"))
    ctx = _trip_context(req)

    # 조식 포함 숙박 박수, 무료 제공 식사 수 (식비 차감용)
    breakfast_nights = sum(int(i.get("nights") or 1) for i in items
                           if classify(i) == "lodging"
                           and (i.get("breakfast_included") or "조식" in _text(i)))
    provided_meals = int(req.get("meals_provided") or 0)

    results = []
    for item in items:
        findings = []
        cat = classify(item)

        if ctx["is_intra_city"]:
            findings += _check_intra_city(item, ctx)
        elif ctx["is_travel"]:
            if cat == "lodging":
                findings += _check_lodging(item, grade, ctx)
            elif cat == "meal":
                findings += _check_meal(item, grade, ctx, breakfast_nights, provided_meals)
            elif cat == "per_diem":
                findings += _check_per_diem(item, grade, ctx)
            elif cat == "transport":
                findings += _check_transport(item, grade, ctx)

        if cat in {"business", "org", "condolence", "wreath"}:
            findings += _check_business(item)
        if item.get("payment") or not ctx["is_travel"] or cat in {"business", "org", "general"}:
            findings += _check_card(item, ctx)

        if not findings:
            findings.append(_finding(item, R.OK, "확인한 규정 기준을 모두 충족합니다.", _default_basis(cat), "", "OK"))
        results += findings

    results += _check_split_payment(items)
    results += _check_trip_bundle(items, ctx, grade)

    overall = max((r["verdict"] for r in results), key=lambda v: R.SEVERITY[v])
    return {"overall": overall, "items": results}


def _default_basis(cat: str) -> str:
    return {
        "lodging": "여비규정 제14조 제2항, 별표 1",
        "meal": "여비규정 제14조 제1항, 별표 1",
        "per_diem": "여비규정 제14조 제1항, 별표 1",
        "transport": "여비규정 제13조, 별표 1",
        "business": "업무추진비 및 조직관리비 집행 지침",
        "org": "업무추진비 및 조직관리비 집행 지침",
        "condolence": "업무추진비 및 조직관리비 집행 지침 제7조",
        "wreath": "업무추진비 및 조직관리비 집행 지침 제7조",
    }.get(cat, "법인카드 관리 및 사용 지침")
