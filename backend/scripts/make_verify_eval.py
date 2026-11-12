# -*- coding: utf-8 -*-
"""청구 검증 평가셋 생성기 — 평가 건을 파이썬으로 읽기 쉽게 적고 data/eval/verify_eval.json 으로 내보냅니다.

    cd backend
    python -m scripts.make_verify_eval

건을 추가·수정할 때는 이 파일에서 case(...) 를 고친 뒤 위 명령으로 JSON 을 다시 만드세요.
기대값은 여비규정·카드 지침 조항과 종원 님 FAQ(오류 매핑·검증 사례)에서 정했고, 엔진 출력을 보고 맞추지 않았습니다.
(예외: 작성 실수로 판명된 건은 note 에 이유를 적고 고쳤습니다.)
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "eval" / "verify_eval.json"

OK, FIX, CHECK = "규정상 확인 가능", "보완 필요", "담당자 확인 필요"
cases = []

def case(cid, cat, name, req, overall, rules=None, source="", note="", disputed=False):
    req = dict(req)
    req.setdefault("trip_type", "국내출장")
    req.setdefault("grade", "직원 3급 이하")
    cases.append({
        "id": cid, "category": cat, "name": name, "source": source, "note": note,
        "disputed": disputed, "request": req,
        "expect": {"overall": overall, "rules": rules or {}},
    })

def R(verdict, basis):  # 기대 규칙: [판정, 근거 조항 문자열]
    return [verdict, basis]

T2 = {"start_date": "2026-10-20", "end_date": "2026-10-21"}   # 1박 2일
# ---------------- 숙박 ----------------
case("L01", "숙박", "서울 1박 150,000원, 사유 없음", {"trip": {**T2, "region": "서울"}, "items": [{"field": "숙박비", "amount": 150000, "nights": 1}]},
     FIX, {"T-LODGING-CAP": R(FIX, "제11조 제6항")}, "별표1, 확정 기준(5주차)")
case("L02", "숙박", "광역시 1박 95,000원, 사유 없음", {"trip": {**T2, "region": "광역시"}, "items": [{"field": "숙박비", "amount": 95000, "nights": 1}]},
     FIX, {"T-LODGING-CAP": R(FIX, "제11조 제6항")}, "별표1, 확정 기준(5주차)")
case("L03", "숙박", "광역시 1박 95,000원, 특례 사유 있음", {"trip": {**T2, "region": "광역시"}, "items": [{"field": "숙박비", "amount": 95000, "nights": 1, "exception_reason": "행사 기간 숙소 부족"}]},
     CHECK, {"T-LODGING-EXTRA": R(CHECK, "제11조 제6항")}, "제11조제6항 특례")
case("L04", "숙박", "기타 1박 120,000원, 특례 사유 있어도 130%(104,000원) 초과", {"trip": {**T2, "region": "기타"}, "items": [{"field": "숙박비", "amount": 120000, "nights": 1, "exception_reason": "행사 기간 숙소 부족"}]},
     FIX, {"T-LODGING-CAP": R(FIX, "제11조 제6항")}, "제11조제6항 특례 한도")
case("L05", "숙박", "기타 1박 80,000원 (상한과 같음)", {"trip": {**T2, "region": "기타"}, "items": [{"field": "숙박비", "amount": 80000, "nights": 1}]}, OK, source="별표1 경계")
case("L06", "숙박", "기타 2박 합계 150,000원 (합계 상한 160,000원 이내)", {"trip": {"start_date": "2026-10-20", "end_date": "2026-10-22", "region": "기타"}, "items": [{"field": "숙박비", "amount": 150000, "nights": 2}]}, OK, source="제14조제2항")
case("L07", "숙박", "서울 1박 100,001원 (상한 +1원), 사유 없음", {"trip": {**T2, "region": "서울"}, "items": [{"field": "숙박비", "amount": 100001, "nights": 1}]},
     FIX, {"T-LODGING-CAP": R(FIX, "제11조 제6항")}, "종원 TC13", "TC13 원본은 담당자 확인이지만 5주차 확정 기준(특례 사유 없으면 상한액 수정)을 적용함")
case("L08", "숙박", "출장지 지역 정보 없음", {"items": [{"field": "숙박비", "amount": 80000, "nights": 1}]}, CHECK, {"T-LODGING-REGION": R(CHECK, "별표 1")}, "별표1")
case("L09", "숙박", "숙박 영수증 없음 (금액은 상한 이내)", {"trip": {**T2, "region": "광역시"}, "items": [{"field": "숙박비", "amount": 85000, "nights": 1, "receipt": False}]},
     FIX, {"T-LODGING-RECEIPT": R(FIX, "제11조 제1항")}, "제11조제1항, 종원 M03")
case("L10", "숙박", "본부장 서울 250,000원 (임원급은 실비)", {"grade": "임원·본부장", "trip": {**T2, "region": "서울"}, "items": [{"field": "숙박비", "amount": 250000, "nights": 1}]}, OK, source="별표1 임원급 실비")
case("L11", "숙박", "세종 1박 90,000원 (세종은 광역시 기준)", {"trip": {**T2, "region": "세종"}, "items": [{"field": "숙박비", "amount": 90000, "nights": 1}]}, OK, source="별표1 주4")
case("L12", "숙박", "제주 1박 85,000원 (제주는 기타 80,000원), 사유 없음", {"trip": {**T2, "region": "제주"}, "items": [{"field": "숙박비", "amount": 85000, "nights": 1}]},
     FIX, {"T-LODGING-CAP": R(FIX, "제11조 제6항")}, "별표1 주4")
# ---------------- 식비 ----------------
case("M01", "식비", "조식 포함 숙박인데 식비 27,000원 전액", {"trip": {**T2, "region": "서울"}, "items": [{"field": "숙박비", "amount": 95000, "nights": 1, "breakfast_included": True}, {"field": "식비", "amount": 27000, "days": 1}]},
     FIX, {"T-MEAL-BREAKFAST": R(FIX, "제11조 제4항")}, "종원 TC05, M08")
case("M02", "식비", "조식 포함 숙박, 식비 18,000원 (1/3 차감 반영)", {"trip": {**T2, "region": "서울"}, "items": [{"field": "숙박비", "amount": 95000, "nights": 1, "breakfast_included": True}, {"field": "식비", "amount": 18000, "days": 1}]}, OK, source="제11조제4항")
case("M03", "식비", "2일 식비 70,000원 (한도 54,000원)", {"trip": {**T2, "region": "서울"}, "items": [{"field": "식비", "amount": 70000, "days": 2}]},
     FIX, {"T-MEAL-CAP": R(FIX, "제14조 제1항")}, "별표1")
case("M04", "식비", "무료 식사 2식 제공인데 식비 27,000원 전액", {"trip": {**T2, "region": "서울"}, "items": [{"field": "식비", "amount": 27000, "days": 1, "meals_provided": 2}]},
     FIX, {"T-MEAL-PROVIDED": R(FIX, "제15조 제2항")}, "종원 TC17, M10")
case("M05", "식비", "2일 식비 54,000원 (한도와 같음)", {"trip": {**T2, "region": "서울"}, "items": [{"field": "식비", "amount": 54000, "days": 2}]}, OK, source="별표1 경계")
# ---------------- 일비 ----------------
case("P01", "일비", "업무용차량 이용인데 일비 60,000원(2일) 전액", {"trip": {**T2, "vehicle": "업무용차량"}, "items": [{"field": "일비", "amount": 60000}]},
     FIX, {"T-PERDIEM-CAR": R(FIX, "제14조 제1항")}, "종원 TC07, M16")
case("P02", "일비", "대중교통 일비 60,000원(2일)", {"trip": {**T2, "vehicle": "대중교통"}, "items": [{"field": "일비", "amount": 60000}]}, OK, source="별표1")
case("P03", "일비", "일비 75,000원 (2일 한도 60,000원)", {"trip": {**T2}, "items": [{"field": "일비", "amount": 75000}]},
     FIX, {"T-PERDIEM-CAP": R(FIX, "제14조 제1항")}, "별표1")
case("P04", "일비", "렌트차량 1일 일비 30,000원", {"trip": {"start_date": "2026-10-20", "end_date": "2026-10-20", "vehicle": "렌트차량"}, "items": [{"field": "일비", "amount": 30000}]},
     FIX, {"T-PERDIEM-CAR": R(FIX, "제14조 제1항")}, "제14조제1항")
# ---------------- 교통 ----------------
case("T01", "교통", "3급 이하 KTX 특실", {"items": [{"field": "철도운임(KTX)", "amount": 59800, "seat_class": "특실"}]},
     FIX, {"T-TRANS-RAIL-CLASS": R(FIX, "별표 1")}, "종원 TC11, TC10, M20")
case("T02", "교통", "3급 이하 KTX 일반실", {"items": [{"field": "철도운임(KTX)", "amount": 47000, "seat_class": "일반"}]}, OK, source="별표1")
case("T03", "교통", "1·2급 KTX 특실 (허용)", {"grade": "직원 1·2급", "items": [{"field": "철도운임(KTX)", "amount": 59800, "seat_class": "특실"}]}, OK, source="별표1")
case("T04", "교통", "직원 국내 항공 비즈니스", {"items": [{"field": "항공운임", "amount": 180000, "seat_class": "비즈니스"}]},
     FIX, {"T-TRANS-AIR-CLASS": R(FIX, "별표 1")}, "종원 TC12, M20")
case("T05", "교통", "KTX 48,000원 승차권·영수증 없음", {"items": [{"field": "철도운임(KTX)", "amount": 48000, "seat_class": "일반", "receipt": False}]},
     FIX, {"T-TRANS-RECEIPT": R(FIX, "제10조 제1항")}, "종원 TC03, M03")
case("T06", "교통", "자가용 이용, 승인 확인 안 됨", {"trip": {"vehicle": "자가용"}, "items": [{"field": "교통비(자가용)", "amount": 40000}]},
     CHECK, {"T-TRANS-PRIVATE-APPROVAL": R(CHECK, "제13조 제5항")}, "종원 M13, TC14", "M13은 담당자 확인, TC14는 보완 필요로 적혀 있어 두 시트가 다름. M13 기준을 따름", disputed=True)
case("T07", "교통", "자가용 승인 있음, 실비 60,000원 > 철도 운임 50,000원", {"trip": {"vehicle": "자가용", "private_car_approved": True}, "items": [{"field": "교통비(자가용)", "amount": 60000, "public_fare": 50000}]},
     FIX, {"T-TRANS-PRIVATE-CAP": R(FIX, "제13조 제6항")}, "종원 TC15, M14")
case("T08", "교통", "자가용 승인 있음, 실비 40,000원 ≤ 운임 50,000원", {"trip": {"vehicle": "자가용", "private_car_approved": True}, "items": [{"field": "교통비(자가용)", "amount": 40000, "public_fare": 50000}]}, OK, source="제13조제6항")
case("T09", "교통", "동승자 교통비 청구", {"items": [{"field": "교통비", "amount": 30000, "note": "동승자 교통비"}]},
     FIX, {"T-TRANS-PASSENGER": R(FIX, "제13조 제7항")}, "종원 TC08, M15")
case("T10", "교통", "업무용 차량 구간 교통비 22,000원", {"trip": {**T2, "vehicle": "업무용차량"}, "items": [{"field": "교통비", "amount": 22000, "note": "업무용차량 구간"}]},
     FIX, {"T-TRANS-COMPANYCAR": R(FIX, "제13조 제3항")}, "종원 TC07, M12")
case("T11", "교통", "KTX 영수증 대신 결재문서, 인가요금 30,000원 < 청구 35,000원", {"items": [{"field": "철도운임(KTX)", "amount": 35000, "seat_class": "일반", "receipt": False, "substitute_approved": True, "authorized_fare": 30000}]},
     FIX, {"T-TRANS-SUBSTITUTE-FARE": R(FIX, "")}, "실무자 의견(2026-11 코칭)")
case("T12", "교통", "KTX 영수증 대신 결재문서, 인가요금 미입력", {"items": [{"field": "철도운임(KTX)", "amount": 35000, "seat_class": "일반", "receipt": False, "substitute_approved": True}]},
     CHECK, {"T-TRANS-SUBSTITUTE-CHECK": R(CHECK, "")}, "실무자 의견(2026-11 코칭)")
# ---------------- 정산 기한 ----------------
case("S01", "정산기한", "출장 종료 후 18일 만에 정산", {"trip": {"start_date": "2026-10-01", "end_date": "2026-10-02", "settlement_date": "2026-10-20", "region": "기타"}, "items": [{"field": "숙박비", "amount": 70000, "nights": 1}]},
     FIX, {"T-LATE-SETTLEMENT": R(FIX, "제3조의2")}, "종원 M01, TC01", "종원 시트는 보완 필요, 엔진·규칙표는 담당자 확인(지연 사유 소명)", disputed=True)
case("S02", "정산기한", "출장 종료 후 정확히 15일째 정산 (기한 이내)", {"trip": {"start_date": "2026-10-01", "end_date": "2026-10-02", "settlement_date": "2026-10-17", "region": "기타"}, "items": [{"field": "숙박비", "amount": 70000, "nights": 1}]}, OK, source="제3조의2제2항 경계")
case("S03", "정산기한", "출장 종료 후 16일째 정산 (1일 초과)", {"trip": {"start_date": "2026-10-01", "end_date": "2026-10-02", "settlement_date": "2026-10-18", "region": "기타"}, "items": [{"field": "숙박비", "amount": 70000, "nights": 1}]},
     FIX, {"T-LATE-SETTLEMENT": R(FIX, "제3조의2")}, "종원 TC01", "S01과 같은 이유로 기준 확정 필요", disputed=True)
# ---------------- 근무지 내 출장 ----------------
case("I01", "근무지내", "왕복 7.9km, 3시간, 교통비 15,000원", {"trip_type": "근무지 내 출장", "trip": {"hours": 3, "round_trip_km": 7.9}, "items": [{"field": "교통비", "amount": 15000}]},
     FIX, {"T-INTRA-DISTANCE": R(FIX, "제16조 제1항")}, "종원 TC06, M11")
case("I02", "근무지내", "왕복 8.0km 정확히, 3시간, 교통비 15,000원 (경계, 탈락 아님)", {"trip_type": "근무지 내 출장", "trip": {"hours": 3, "round_trip_km": 8}, "items": [{"field": "교통비", "amount": 15000}]}, OK, source="종원 TC06 경계")
case("I03", "근무지내", "근무지 내 출장인데 식비 청구", {"trip_type": "근무지 내 출장", "trip": {"hours": 5, "round_trip_km": 20}, "items": [{"field": "식비", "amount": 9000}]},
     FIX, {"T-INTRA-ONLY-FARE": R(FIX, "제16조 제1항")}, "제16조제1항")
case("I04", "근무지내", "3시간 출장 교통비 20,000원 (정액 15,000원)", {"trip_type": "근무지 내 출장", "trip": {"hours": 3, "round_trip_km": 12}, "items": [{"field": "교통비", "amount": 20000}]},
     FIX, {"T-INTRA-FARE": R(FIX, "제16조 제1항")}, "M11")
case("I05", "근무지내", "5시간 출장 교통비 30,000원 (정액과 같음)", {"trip_type": "근무지 내 출장", "trip": {"hours": 5, "round_trip_km": 20}, "items": [{"field": "교통비", "amount": 30000}]}, OK, source="M11 경계")
# ---------------- 법인카드 ----------------
case("C01", "법인카드", "유흥주점 사용", {"trip_type": "법인카드", "items": [{"field": "회식비", "amount": 120000, "date": "2026-10-22", "time": "20:00", "payment": "법인카드", "merchant": "OO 유흥주점", "merchant_type": "유흥주점"}]},
     FIX, {"C-BANNED-MERCHANT": R(FIX, "제10조")}, "카드 지침 제10조제3항")
case("C02", "법인카드", "23:30 사용, 사유서 없음", {"trip_type": "법인카드", "items": [{"field": "회의 식대", "amount": 80000, "date": "2026-10-21", "time": "23:30", "payment": "법인카드"}]},
     FIX, {"C-ODD-HOURS": R(FIX, "제10조")}, "카드 지침 제10조제4항2호")
case("C03", "법인카드", "23:30 사용, 사유서 있음", {"trip_type": "법인카드", "items": [{"field": "회의 식대", "amount": 80000, "date": "2026-10-21", "time": "23:30", "payment": "법인카드", "reason_doc": True}]},
     CHECK, {"C-ODD-HOURS": R(CHECK, "제10조")}, "카드 지침 제10조제4항2호")
case("C04", "법인카드", "한글날(10/9) 공휴일 사용, 사유서 없음", {"trip_type": "법인카드", "items": [{"field": "회의 식대", "amount": 60000, "date": "2026-10-09", "time": "12:30", "payment": "법인카드"}]},
     FIX, {"C-HOLIDAY": R(FIX, "제10조")}, "카드 지침 제10조제4항1호")
case("C05", "법인카드", "토요일(10/24) 사용, 사유서 없음", {"trip_type": "법인카드", "items": [{"field": "회의 식대", "amount": 60000, "date": "2026-10-24", "time": "12:30", "payment": "법인카드"}]},
     FIX, {"C-HOLIDAY": R(FIX, "제10조")}, "카드 지침 제10조제4항1호")
case("C06", "법인카드", "개인카드 사용분을 법인비용으로 청구", {"trip_type": "법인카드", "items": [{"field": "회의 식대", "amount": 50000, "date": "2026-10-22", "time": "12:30", "payment": "개인카드"}]},
     FIX, {"C-PERSONAL-CARD": R(FIX, "제7조"), "B-CARD-ONLY": R(FIX, "제4조")}, "카드 지침 제7조제6항", "'회의 식대'는 업무추진비로 분류되므로 업무추진비의 법인카드 외 지출(B-CARD-ONLY)도 함께 해당")
case("C07", "법인카드", "기타주점(호프) 사용, 사유서 없음", {"trip_type": "법인카드", "items": [{"field": "회식비", "amount": 90000, "date": "2026-10-22", "time": "19:00", "payment": "법인카드", "merchant": "OO호프", "merchant_type": "기타주점업"}]},
     FIX, {"C-OTHER-BAR": R(FIX, "제10조")}, "카드 지침 제10조제4항4호")
case("C08", "법인카드", "평일 낮 한식당 점심 (정상)", {"trip_type": "법인카드", "items": [{"field": "회의 식대", "amount": 60000, "date": "2026-10-22", "time": "12:20", "payment": "법인카드", "merchant": "OO식당", "merchant_type": "한식"}]}, OK, source="정상 사례")
# ---------------- 업무추진비 ----------------
case("B01", "업무추진비", "62만원 사전결재 없음", {"trip_type": "업무추진비", "items": [{"field": "업무추진비(간담회)", "amount": 620000, "date": "2026-10-22", "payment": "법인카드", "attendees": ["해양수산부 OOO 과장"]}]},
     FIX, {"B-PRE-APPROVAL": R(FIX, "제3조")}, "업무추진비 지침 제3조제4항")
case("B02", "업무추진비", "120만원 사전결재 있음, 일상감사 없음", {"trip_type": "업무추진비", "items": [{"field": "업무추진비(간담회)", "amount": 1200000, "date": "2026-10-22", "payment": "법인카드", "pre_approved": True, "attendees": ["해양수산부 OOO 과장"]}]},
     FIX, {"B-DAILY-AUDIT": R(FIX, "제3조")}, "업무추진비 지침 제3조제4항")
case("B03", "업무추진비", "45만원 참석자 기재, 정상", {"trip_type": "업무추진비", "items": [{"field": "업무추진비(간담회)", "amount": 450000, "date": "2026-10-22", "payment": "법인카드", "attendees": ["해양수산부 OOO 과장"], "counterpart_info": True}]}, OK, source="정상 사례")
case("B04", "업무추진비", "같은 날 같은 거래처 30만원 + 30만원 분할결제", {"trip_type": "업무추진비", "items": [
        {"field": "업무추진비(간담회)", "amount": 300000, "date": "2026-10-22", "payment": "법인카드", "merchant": "OO식당", "attendees": ["해양수산부 OOO 과장"]},
        {"field": "업무추진비(간담회)", "amount": 300000, "date": "2026-10-22", "payment": "법인카드", "merchant": "OO식당", "attendees": ["해양수산부 OOO 과장"]}]},
     FIX, {"B-SPLIT-PAYMENT": R(FIX, "제3조")}, "업무추진비 지침 제3조제5항")
case("B05", "업무추진비", "30만원 상대방 정보 없음", {"trip_type": "업무추진비", "items": [{"field": "업무추진비(간담회)", "amount": 300000, "date": "2026-10-22", "payment": "법인카드"}]},
     FIX, {"B-COUNTERPART": R(FIX, "제8조")}, "업무추진비 지침 제8조제1항")
case("B06", "업무추진비", "경조금 6만원 (한도 5만원)", {"trip_type": "업무추진비", "items": [{"field": "경조금", "amount": 60000, "date": "2026-10-22", "payment": "법인카드"}]},
     FIX, {"B-CONDOLENCE-CAP": R(FIX, "제7조")}, "업무추진비 지침 제7조")
case("B07", "업무추진비", "화환 12만원 (한도 10만원)", {"trip_type": "업무추진비", "items": [{"field": "화환", "amount": 120000, "date": "2026-10-22", "payment": "법인카드"}]},
     FIX, {"B-WREATH-CAP": R(FIX, "제7조")}, "업무추진비 지침 제7조")
case("B08", "업무추진비", "업무추진비를 현금으로 지출", {"trip_type": "업무추진비", "items": [{"field": "업무추진비(간담회)", "amount": 200000, "date": "2026-10-22", "payment": "현금", "attendees": ["해양수산부 OOO 과장"]}]},
     FIX, {"B-CARD-ONLY": R(FIX, "제4조")}, "업무추진비 지침 제4조제1항")
# ---------------- 복합 / 정상 ----------------
case("X01", "복합", "서울 1박 출장, 모두 규정 이내", {"trip": {**T2, "region": "서울", "settlement_date": "2026-10-25"}, "items": [
        {"field": "철도운임(KTX)", "amount": 47000, "seat_class": "일반"}, {"field": "일비", "amount": 60000}, {"field": "식비", "amount": 54000}, {"field": "숙박비", "amount": 95000, "nights": 1}]}, OK, source="정상 사례")
case("X02", "복합", "조식 포함 식비 미차감 + 숙박 상한 초과 동시", {"trip": {**T2, "region": "서울"}, "items": [
        {"field": "숙박비", "amount": 150000, "nights": 1, "breakfast_included": True}, {"field": "식비", "amount": 27000, "days": 1}]},
     FIX, {"T-LODGING-CAP": R(FIX, "제11조 제6항"), "T-MEAL-BREAKFAST": R(FIX, "제11조 제4항")}, "여러 규칙 동시 탐지")
case("X03", "복합", "자가용 승인 없음 + 동승자 교통비", {"trip": {"vehicle": "자가용"}, "items": [
        {"field": "교통비(자가용)", "amount": 40000}, {"field": "교통비", "amount": 20000, "note": "동승자 교통비"}]},
     FIX, {"T-TRANS-PRIVATE-APPROVAL": R(CHECK, "제13조 제5항"), "T-TRANS-PASSENGER": R(FIX, "제13조 제7항")}, "종원 TC08", "TC08은 '보완 필요 + 담당자 확인 필요' 복합 결과")

# ---------------- 경계·표현 변형 ----------------
case("Q01", "경계·변형", "특례 사유 있고 숙박비가 정확히 130%(104,000원)", {"trip": {**T2, "region": "기타"}, "items": [{"field": "숙박비", "amount": 104000, "nights": 1, "exception_reason": "행사 기간 숙소 부족"}]},
     CHECK, {"T-LODGING-EXTRA": R(CHECK, "제11조 제6항")}, "제11조제6항 경계")
case("Q02", "경계·변형", "특례 사유 있고 숙박비 104,001원 (130% +1원)", {"trip": {**T2, "region": "기타"}, "items": [{"field": "숙박비", "amount": 104001, "nights": 1, "exception_reason": "행사 기간 숙소 부족"}]},
     FIX, {"T-LODGING-CAP": R(FIX, "제11조 제6항")}, "제11조제6항 경계")
case("Q03", "경계·변형", "기타 2박 170,000원 (합계 상한 160,000원), 사유 없음", {"trip": {"start_date": "2026-10-20", "end_date": "2026-10-22", "region": "기타"}, "items": [{"field": "숙박비", "amount": 170000, "nights": 2}]},
     FIX, {"T-LODGING-CAP": R(FIX, "제11조 제6항")}, "제14조제2항")
case("Q04", "경계·변형", "항목 메모에만 '조식 포함 숙박'이라고 적은 식비 27,000원", {"trip": {"region": "기타"}, "items": [{"field": "식비", "amount": 27000, "date": "2026-10-20", "note": "조식 포함 숙박"}]},
     FIX, {"T-MEAL-BREAKFAST": R(FIX, "제11조 제4항")}, "API.md 7절 사례 (메모 문장 입력)")
case("Q05", "경계·변형", "메모에만 '특실 이용'이라고 적은 KTX 운임", {"items": [{"field": "KTX 운임", "amount": 59800, "note": "특실 이용"}]},
     FIX, {"T-TRANS-RAIL-CLASS": R(FIX, "별표 1")}, "별표1 (메모 문장 입력)")
case("Q06", "경계·변형", "조식 포함 + 행사 점심 제공인데 식비 18,000원 (조식분만 차감)", {"trip": {**T2, "region": "서울"}, "items": [{"field": "숙박비", "amount": 95000, "nights": 1, "breakfast_included": True}, {"field": "식비", "amount": 18000, "days": 1, "meals_provided": 1}]},
     FIX, {"T-MEAL-BREAKFAST": R(FIX, "제11조 제4항")}, "종원 TC17 (조식+점심 각각 공제)")
# ---------------- 종원 오류 매핑 중 엔진에 규칙이 없을 수 있는 유형 ----------------
case("N01", "오류유형 확대", "카드 매입 통보가 늦어 7일 예외 적용 (지연 증빙 있음)", {"trip": {"start_date": "2026-10-30", "end_date": "2026-11-01", "settlement_date": "2026-11-22", "region": "기타"}, "items": [{"field": "숙박비", "amount": 70000, "nights": 1, "card_notice_at": "2026-11-17", "late_notice_proof": True}]},
     CHECK, {}, "종원 M02, TC02", "M02는 담당자 확인, TC02는 규정상 확인 가능(기한 규칙 단독)으로 시트끼리 다름", disputed=True)
case("N02", "오류유형 확대", "신청 금액 50,000원, 영수증 금액 45,000원, 차이 사유 없음", {"trip": {**T2, "region": "기타"}, "items": [{"field": "숙박비", "amount": 50000, "nights": 1, "receipt_amount": 45000}]},
     FIX, {}, "종원 M05")
case("N03", "오류유형 확대", "숙박 부대비 8,000원 + 숙박비 85,000원 (총액이 광역시 상한 90,000원 초과)", {"trip": {**T2, "region": "광역시"}, "items": [{"field": "숙박비", "amount": 85000, "nights": 1}, {"field": "숙박 부대비", "amount": 8000}]},
     FIX, {}, "종원 M07, 제11조제5항")
case("N04", "오류유형 확대", "무료 숙박이 제공된 밤인데 숙박비 80,000원 청구", {"trip": {**T2, "region": "기타"}, "items": [{"field": "숙박비", "amount": 80000, "nights": 1, "lodging_provided": True, "note": "숙박 무료 제공"}]},
     FIX, {}, "종원 M09, TC09, 제15조제2항제1호")
case("N05", "오류유형 확대", "교육출장 일비 3일 청구 (출발·복귀일 합계 2일 한도)", {"trip": {"start_date": "2026-10-20", "end_date": "2026-10-22", "training_flag": True}, "items": [{"field": "일비", "amount": 90000, "note": "교육출장"}]},
     FIX, {}, "종원 M17, 제14조제1항 단서")
case("N06", "오류유형 확대", "주최 측이 교통비를 지원했는데 교통비도 청구", {"trip": {**T2}, "items": [{"field": "교통비", "amount": 30000, "note": "주최 측 교통비 지원", "third_party_subsidy": 30000}]},
     CHECK, {}, "종원 M18, 제15조제1항")
case("N07", "오류유형 확대", "숙박 영수증 날짜(10/25)가 출장 일정(10/20~21)과 다름", {"trip": {**T2, "region": "기타"}, "items": [{"field": "숙박비", "amount": 70000, "nights": 1, "date": "2026-10-25"}]},
     CHECK, {}, "종원 M21")
case("N08", "오류유형 확대", "개정일(2026-10-21) 이전 출장(10/15)", {"trip": {"start_date": "2026-10-15", "end_date": "2026-10-16", "region": "기타"}, "items": [{"field": "숙박비", "amount": 70000, "nights": 1}]},
     CHECK, {}, "종원 TC18, 부칙")

MAPPING = {"L01":["M06"],"L02":["M06"],"L03":["M06"],"L04":["M06"],"L07":["M06"],"L12":["M06"],"Q01":["M06"],"Q02":["M06"],"Q03":["M06"],"L09":["M03"],"T05":["M03"],"M01":["M08"],"Q04":["M08"],"Q06":["M08"],"M04":["M10"],"I01":["M11"],"I02":["M11"],"I03":["M11"],"I04":["M11"],"I05":["M11"],"T10":["M12"],"T06":["M13"],"T07":["M14"],"T08":["M14"],"T09":["M15"],"P01":["M16"],"P04":["M16"],"T01":["M20"],"T04":["M20"],"Q05":["M20"],"S01":["M01"],"S03":["M01"],"N01":["M02"],"N02":["M05"],"N03":["M07"],"N04":["M09"],"N05":["M17"],"N06":["M18"],"N07":["M21"],"N08":["TC18"]}
for c in cases: c["mapping"] = MAPPING.get(c["id"], [])

json.dump({"version": "2026-11-12", "verdict_names": [OK, FIX, CHECK], "cases": cases},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(cases), "cases")
