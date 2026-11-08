"""
U-05 출장비 자동 계산 (국내 출장)

출장 정보를 넣으면 여비규정 별표 1 기준으로 받을 수 있는 금액을 항목별로 계산하고,
계산식과 적용 조항을 함께 돌려줍니다.

    from app.precheck import calc_travel
    result = calc_travel(request_json)

- 일비·식비: 정액 → 바로 금액이 나옴
- 숙박비: 실비 정산이라 "상한"을 알려줌 (실제 숙박비는 영수증 금액)
- 교통비: 실비. 입력한 운임은 그대로 담고, 자가용은 유류비를 계산해 대중교통 운임 한도와 비교
- 결과의 `verify_request` 를 U-04 `/api/verify` 에 그대로 보내면 사전검증까지 이어짐

판단이 필요한 부분(자가용 승인, 숙박 상한 30% 추가 등)은 계산하지 않고 `notes` 로 안내합니다.
"""

from __future__ import annotations

from . import rules as R
from .engine import _parse_date, _won, normalize_grade


def _line(field, amount, kind, formula, basis, note=""):
    return {"field": field, "amount": amount, "type": kind,
            "formula": formula, "basis": basis, "note": note}


def _per_diem_amount(daily, days, company_car, education):
    """일비: 정액, 업무용·렌트 차량이면 1/2, 교육 출장은 2일 한도, 장기 체류 감액."""
    paid_days = min(days, R.EDU_PER_DIEM_MAX_DAYS) if education else days
    ratio = R.COMPANY_CAR_PER_DIEM_RATIO if company_car else 1
    total = 0
    reduced = {"10": 0, "30": 0}
    for i in range(paid_days):          # i = 0 은 도착일, i >= 1 은 "도착 다음날부터 i일째"
        rate = 1.0
        if i > R.LONG_STAY_30PCT_AFTER:
            rate, key = 0.7, "30"
        elif i > R.LONG_STAY_10PCT_AFTER:
            rate, key = 0.9, "10"
        else:
            key = None
        if key:
            reduced[key] += 1
        total += daily * ratio * rate
    return int(round(total)), paid_days, reduced


def calc_travel(req: dict) -> dict:
    trip_type = str(req.get("trip_type") or "국내출장").replace(" ", "")
    grade = normalize_grade(req.get("grade"))
    row = R.DOMESTIC_TABLE[grade]
    trip = dict(req.get("trip") or {})
    for k in ("start_date", "end_date", "region", "vehicle", "hours", "round_trip_km",
              "purpose", "breakfast_nights", "meals_provided", "lodging_provided", "nights"):
        if k not in trip and k in req:
            trip[k] = req[k]

    vehicle = str(trip.get("vehicle") or "대중교통").replace(" ", "")
    company_car = vehicle in {v.replace(" ", "") for v in R.COMPANY_VEHICLES}
    private_car = vehicle in R.PRIVATE_CAR
    lines, notes = [], []

    # ------------------------------------------------------------------ 근무지 내 출장
    if "근무지내" in trip_type:
        hours = trip.get("hours")
        km = trip.get("round_trip_km")
        if company_car:
            fare, formula = 0, "업무용 차량 이용 → 교통비 없음"
        elif km is not None and float(km) < R.INTRA_CITY_MIN_KM:
            fare, formula = 0, f"왕복 {km}km < {R.INTRA_CITY_MIN_KM}km → 교통비 없음"
        elif hours is None:
            fare, formula = None, "출장시간을 입력하면 정액이 정해집니다 (4시간 이상 30,000원 / 미만 15,000원)"
        else:
            long_ = float(hours) >= 4
            fare = R.INTRA_CITY_FARE_LONG if long_ else R.INTRA_CITY_FARE_SHORT
            formula = f"출장시간 {hours}시간 {'≥' if long_ else '<'} 4시간 → {_won(fare)} 정액"
        lines.append(_line("교통비", fare, "정액", formula, "여비규정 제16조 제1항"))
        notes.append("근무지 내 출장(같은 시·군)은 교통비만 지급되고 일비·식비·숙박비는 없습니다.")
        return _result(grade, trip_type, None, 0, 0, lines, notes, trip)

    # ------------------------------------------------------------------ 근무지 외 국내출장
    start, end = _parse_date(trip.get("start_date")), _parse_date(trip.get("end_date"))
    if start and end and end >= start:
        days = (end - start).days + 1
    else:
        days = int(trip.get("days") or 1)
        notes.append("출장 날짜가 없어 1일 출장으로 계산했습니다.")
    nights = int(trip["nights"]) if trip.get("nights") is not None else max(days - 1, 0)
    region = R.REGION_ALIASES.get(str(trip.get("region", "")).strip())
    education = "교육" in str(trip.get("purpose") or "")

    # 일비
    daily = row["per_diem"]
    per_diem, paid_days, reduced = _per_diem_amount(daily, days, company_car, education)
    formula = f"{_won(daily)} × {paid_days}일"
    if company_car:
        formula += " × 1/2 (업무용·렌트 차량)"
    basis = "여비규정 제14조 제1항, 별표 1"
    if reduced["10"] or reduced["30"]:
        formula += f" (장기 체류 감액: 1할 {reduced['10']}일, 3할 {reduced['30']}일)"
        basis += ", 제14조 제4항"
        notes.append("60일을 넘게 같은 지역에 체류하면 여비담당부서장의 사전승인이 필요합니다 (제14조 제4항).")
    if education and days > R.EDU_PER_DIEM_MAX_DAYS:
        formula += " (교육 출장은 출발일·복귀일 2일 한도)"
    lines.append(_line("일비", per_diem, "정액", formula, basis))

    # 식비
    meal_daily = row["meal"]
    meal = meal_daily * days
    meal_formula = f"{_won(meal_daily)} × {days}일"
    breakfast = int(trip.get("breakfast_nights") or 0)
    provided = int(trip.get("meals_provided") or 0)
    if breakfast:
        meal -= meal_daily / 3 * breakfast
        meal_formula += f" − 조식 포함 {breakfast}박 × {_won(meal_daily / 3)}"
    if provided:
        meal -= meal_daily / 3 * provided
        meal_formula += f" − 제공 식사 {provided}회 × {_won(meal_daily / 3)}"
    meal_basis = "여비규정 제14조 제1항, 별표 1"
    if breakfast:
        meal_basis += ", 제11조 제4항"
    if provided:
        meal_basis += ", 제15조 제2항"
    lines.append(_line("식비", max(int(round(meal)), 0), "정액", meal_formula, meal_basis))
    notes.append("출장 중 법인카드로 식사했다면 식비 중복 여부를 담당자가 확인합니다 (실무자 의견 기반 가정).")

    # 숙박비 (실비, 상한)
    if nights:
        if trip.get("lodging_provided"):
            lines.append(_line("숙박비", 0, "감액", "주최 측 숙박 무료 제공 → 숙박비 전액 감액",
                               "여비규정 제15조 제2항"))
        elif row["lodging"] is None:
            lines.append(_line("숙박비", None, "실비", f"{nights}박 실비 (상한 없음)", "여비규정 별표 1"))
        elif not region:
            lines.append(_line("숙박비", None, "상한(실비)",
                               "출장지(서울/광역시/기타)를 입력하면 상한이 계산됩니다",
                               "여비규정 제14조 제2항, 별표 1"))
        else:
            cap_1 = row["lodging"][region]
            cap = cap_1 * nights
            extra = int(cap * (1 + R.LODGING_EXTRA_RATIO))
            lines.append(_line("숙박비", cap, "상한(실비)",
                               f"{region} {_won(cap_1)} × {nights}박",
                               "여비규정 제14조 제2항, 별표 1",
                               f"영수증 금액으로 실비 정산. 부득이한 사유가 있으면 {_won(extra)}까지 가능 (제11조 제6항)"))

    # 교통비 (실비)
    for f in req.get("fares") or []:
        kind = str(f.get("type") or "교통비")
        seat = f.get("seat_class")
        lines.append(_line(f"{kind}운임" if not kind.endswith("운임") else kind, int(f.get("amount") or 0), "실비",
                           f"입력 운임{f' ({seat})' if seat else ''}",
                           "여비규정 제13조 제1항, 별표 1",
                           f"{grade} 철도 {'일반실' if row['rail'] == '일반' else row['rail']}·항공 {row['air']} 기준"))
        if seat:
            lines[-1]["seat_class"] = seat

    if company_car:
        notes.append("업무용 차량 이용 구간은 교통비가 없고, 통행료·주차비만 증빙으로 실비 청구합니다 (제13조 제3항).")
    if private_car:
        lines.append(_private_car_line(trip, req))
        notes.append("자가용은 출장승인권자가 인정한 경우에만 가능합니다 (제13조 제5항).")

    return _result(grade, trip_type, region, days, nights, lines, notes, trip)


def _fuel_type(raw):
    """'휘발유'·'가솔린'·'EV' 같은 입력을 연비표의 유종 이름으로 맞춤. 모르면 None."""
    text = str(raw or "").strip()
    if text in R.FUEL_EFFICIENCY:
        return text
    return R.FUEL_ALIASES.get(text.lower())


def _private_car_line(trip, req):
    car = dict(req.get("private_car") or {})
    km = car.get("distance_km")
    if km is None:
        return _line("교통비(자가용)", None, "실비(한도)",
                     "왕복 거리를 입력하면 유류비를 계산합니다",
                     "여비규정 제13조 제6항, 별표 1 주2)")
    d = R.FUEL_DEFAULTS
    fuel = _fuel_type(car.get("fuel"))
    note = ""
    if fuel is None:
        fuel = R.DEFAULT_FUEL
        note += f"차량 유형을 알 수 없어 {fuel} 기준으로 계산했습니다. "
    if fuel in R.ELECTRIC_FUELS:
        price = car.get("price_per_kwh", d["price_per_kwh"])
        eff = car.get("km_per_kwh", R.FUEL_EFFICIENCY[fuel])
        unit, price_given = "km/kWh", "price_per_kwh" in car
    else:
        price = car.get("price_per_liter", d["price_per_liter"])
        eff = car.get("km_per_liter", R.FUEL_EFFICIENCY[fuel])
        unit, price_given = "km/L", "price_per_liter" in car
    fuel_cost = km / eff * price
    formula = f"{km}km ÷ {eff}{unit}({fuel}) × {_won(price)}/{unit.split('/')[1]}"
    tolls = int(car.get("tolls") or 0)
    total = int(round(fuel_cost)) + tolls
    if tolls:
        formula += f" + 통행료 {_won(tolls)}"
    note += f"유류비 산식은 {R.FUEL_BASIS}입니다. "
    if not price_given:
        note += f"단가는 {d['basis_date']}이니 출장일 단가를 입력하세요. "
    fare = car.get("public_fare")
    if fare is not None and total > fare:
        formula += f" = {_won(total)} → 대중교통 운임 {_won(fare)} 한도 적용"
        total = int(fare)
    elif fare is None:
        note += "같은 구간 철도·버스 운임을 넘을 수 없으니 운임을 입력해 확인하세요."
    return _line("교통비(자가용)", total, "실비(한도)", formula,
                 "여비규정 제13조 제6항, 별표 1 주2)", note.strip())


def _result(grade, trip_type, region, days, nights, lines, notes, trip):
    fixed = sum(l["amount"] or 0 for l in lines if l["type"] in {"정액"})
    actual = sum(l["amount"] or 0 for l in lines if l["type"] in {"실비", "실비(한도)"})
    lodging_cap = sum(l["amount"] or 0 for l in lines if l["type"] == "상한(실비)")

    verify_items = []
    for l in lines:
        if l["amount"] is None:
            continue
        item = {"field": l["field"], "amount": l["amount"]}
        if l["field"] == "숙박비" and nights:
            item["nights"] = nights
            if trip.get("breakfast_nights"):
                item["breakfast_included"] = True
        if l["field"] == "식비":
            item["days"] = days
        if l.get("seat_class"):
            item["seat_class"] = l["seat_class"]
        verify_items.append(item)

    verify_request = {
        "trip_type": "근무지 내 출장" if "근무지내" in trip_type else "국내출장",
        "grade": grade,
        "trip": {k: trip[k] for k in ("start_date", "end_date", "region", "vehicle",
                                      "private_car_approved", "hours", "round_trip_km") if k in trip},
        "items": verify_items,
    }

    return {
        "grade": grade,
        "trip_type": trip_type,
        "region": region,
        "days": days,
        "nights": nights,
        "lines": lines,
        "summary": {
            "fixed_total": fixed,             # 일비 + 식비 (정액)
            "lodging_cap": lodging_cap,       # 숙박비 상한 합계 (실비 정산)
            "transport_total": actual,        # 입력·계산된 교통비
            "estimated_max": fixed + lodging_cap + actual,
        },
        "notes": notes,
        "verify_request": verify_request,     # U-04 /api/verify 요청으로 그대로 사용 가능
    }
