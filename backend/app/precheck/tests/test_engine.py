"""
U-04 사전검증 엔진 테스트.

실행 (backend 폴더에서):
    python -m unittest discover -s app/precheck/tests -v

케이스 1~7은 docs/API.md 7절 "목업 데이터에 쓸 검증 사례"와 같습니다.
나머지는 규정 원문에서 추가로 뽑은 케이스입니다.
"""

import unittest

from app.precheck import verify_claim
from app.precheck.rules import OK, FIX, CHECK


def run(**req):
    req.setdefault("trip_type", "국내출장")
    req.setdefault("grade", "직원 3급 이하")
    return verify_claim(req)


def find(result, rule_id):
    hits = [r for r in result["items"] if r["rule_id"] == rule_id]
    assert hits, f"{rule_id} 판정이 없습니다: {[r['rule_id'] for r in result['items']]}"
    return hits[0]


class ApiDocCases(unittest.TestCase):
    """docs/API.md 7절 사례"""

    def test_api_example_request(self):
        """API.md 3-2 요청 예시 그대로 넣었을 때 목업과 같은 판정이 나오는지"""
        res = run(trip={"region": "기타"}, items=[
            {"field": "식비", "amount": 27000, "date": "2026-10-20", "note": "조식 포함 숙박"},
            {"field": "숙박비", "amount": 80000, "date": "2026-10-20", "note": ""},
        ])
        self.assertEqual(res["overall"], FIX)
        meal = find(res, "T-MEAL-BREAKFAST")
        self.assertEqual(meal["basis"], "여비규정 제11조 제4항")
        self.assertIn("18,000원", meal["fix"])
        lodging = [r for r in res["items"] if r["field"] == "숙박비"][0]
        self.assertEqual(lodging["verdict"], OK)

    def test_1_breakfast_included(self):
        res = run(trip={"region": "서울"}, items=[
            {"field": "숙박비", "amount": 95000, "nights": 1, "breakfast_included": True},
            {"field": "식비", "amount": 27000, "days": 1},
        ])
        self.assertEqual(find(res, "T-MEAL-BREAKFAST")["verdict"], FIX)

    def test_2_private_car_without_approval(self):
        res = run(trip={"vehicle": "자가용"}, items=[
            {"field": "교통비(자가용)", "amount": 40000},
        ])
        self.assertEqual(find(res, "T-TRANS-PRIVATE-APPROVAL")["verdict"], CHECK)
        self.assertEqual(res["overall"], CHECK)

    def test_3_passenger_fare(self):
        res = run(items=[{"field": "교통비", "amount": 30000, "note": "동승자 교통비"}])
        self.assertEqual(find(res, "T-TRANS-PASSENGER")["verdict"], FIX)

    def test_4_company_car_full_per_diem(self):
        res = run(trip={"start_date": "2026-10-20", "end_date": "2026-10-21", "vehicle": "업무용차량"},
                  items=[{"field": "일비", "amount": 60000}])
        hit = find(res, "T-PERDIEM-CAR")
        self.assertEqual(hit["verdict"], FIX)
        self.assertIn("30,000원", hit["fix"])

    def test_5_late_settlement(self):
        res = run(trip={"start_date": "2026-10-01", "end_date": "2026-10-02",
                        "settlement_date": "2026-10-20", "region": "기타"},
                  items=[{"field": "숙박비", "amount": 70000, "nights": 1}])
        self.assertEqual(find(res, "T-LATE-SETTLEMENT")["verdict"], CHECK)

    def test_6_card_odd_hours(self):
        res = run(trip_type="법인카드", items=[
            {"field": "회의 식대", "amount": 80000, "date": "2026-10-21", "time": "23:30",
             "payment": "법인카드"},
        ])
        hit = find(res, "C-ODD-HOURS")
        self.assertEqual(hit["verdict"], FIX)
        self.assertIn("별지 제5호", hit["fix"])

        res2 = run(trip_type="법인카드", items=[
            {"field": "회의 식대", "amount": 80000, "date": "2026-10-21", "time": "23:30",
             "payment": "법인카드", "reason_doc": True},
        ])
        self.assertEqual(find(res2, "C-ODD-HOURS")["verdict"], CHECK)

    def test_7_business_over_500k_without_pre_approval(self):
        res = run(trip_type="업무추진비", items=[
            {"field": "업무추진비(간담회)", "amount": 620000, "date": "2026-10-22",
             "payment": "법인카드", "attendees": ["해양수산부 OOO 과장"]},
        ])
        self.assertEqual(find(res, "B-PRE-APPROVAL")["verdict"], FIX)


class TravelRules(unittest.TestCase):
    """여비규정 추가 케이스"""

    def test_clean_trip_is_ok(self):
        res = run(trip={"start_date": "2026-10-20", "end_date": "2026-10-21", "region": "광역시",
                        "settlement_date": "2026-10-25"},
                  items=[
                      {"field": "철도운임(KTX)", "amount": 47000, "seat_class": "일반"},
                      {"field": "일비", "amount": 60000},
                      {"field": "식비", "amount": 54000},
                      {"field": "숙박비", "amount": 88000, "nights": 1},
                  ])
        self.assertEqual(res["overall"], OK)

    def test_lodging_within_30_percent_needs_review(self):
        res = run(trip={"region": "기타"}, items=[{"field": "숙박비", "amount": 100000, "nights": 1}])
        self.assertEqual(find(res, "T-LODGING-EXTRA")["verdict"], CHECK)

    def test_lodging_over_30_percent(self):
        res = run(trip={"region": "기타"}, items=[{"field": "숙박비", "amount": 120000, "nights": 1}])
        hit = find(res, "T-LODGING-CAP")
        self.assertEqual(hit["verdict"], FIX)
        self.assertIn("104,000원", hit["fix"])

    def test_lodging_total_cap_over_nights(self):
        """제14조②: 2박이면 상한 합계(160,000원) 안에서 실비 인정"""
        res = run(trip={"region": "기타"}, items=[{"field": "숙박비", "amount": 150000, "nights": 2}])
        self.assertEqual(res["overall"], OK)

    def test_lodging_without_region(self):
        res = run(items=[{"field": "숙박비", "amount": 80000}])
        self.assertEqual(find(res, "T-LODGING-REGION")["verdict"], CHECK)

    def test_executive_lodging_is_actual_cost(self):
        res = run(grade="본부장", trip={"region": "서울"}, items=[{"field": "숙박비", "amount": 250000}])
        self.assertEqual(res["overall"], OK)

    def test_rail_first_class_for_grade3(self):
        res = run(items=[{"field": "철도운임", "amount": 70000, "note": "KTX 특실"}])
        self.assertEqual(find(res, "T-TRANS-RAIL-CLASS")["verdict"], FIX)

    def test_rail_first_class_ok_for_grade2(self):
        res = run(grade="직원 2급", items=[{"field": "철도운임", "amount": 70000, "note": "KTX 특실"}])
        self.assertEqual(res["overall"], OK)

    def test_private_car_over_public_fare(self):
        res = run(trip={"vehicle": "자가용", "private_car_approved": True}, items=[
            {"field": "교통비(자가용)", "amount": 60000, "public_fare": 47000},
        ])
        self.assertEqual(find(res, "T-TRANS-PRIVATE-CAP")["verdict"], FIX)
        self.assertEqual(res["overall"], FIX)

    def test_meal_over_daily_limit(self):
        res = run(trip={"start_date": "2026-10-20", "end_date": "2026-10-20"},
                  items=[{"field": "식비", "amount": 35000}])
        self.assertEqual(find(res, "T-MEAL-CAP")["verdict"], FIX)

    def test_card_meal_during_trip_with_meal_allowance(self):
        """출장 묶음 검증: 법인카드 식사 + 식비 정액 동시 청구"""
        res = run(trip={"start_date": "2026-10-20", "end_date": "2026-10-21", "region": "기타"},
                  items=[
                      {"field": "식비", "amount": 54000},
                      {"field": "저녁 식대", "amount": 25000, "date": "2026-10-20", "payment": "법인카드"},
                  ])
        self.assertEqual(find(res, "T-MEAL-CARD-DUP")["verdict"], CHECK)

    def test_intra_city_trip(self):
        res = run(trip_type="근무지 내 출장", trip={"hours": 3}, items=[
            {"field": "교통비", "amount": 30000},
            {"field": "식비", "amount": 10000},
        ])
        self.assertEqual(find(res, "T-INTRA-FARE")["verdict"], FIX)
        self.assertEqual(find(res, "T-INTRA-ONLY-FARE")["verdict"], FIX)


class CardAndBusinessRules(unittest.TestCase):
    """법인카드 지침 · 업무추진비 지침 추가 케이스"""

    def test_banned_merchant(self):
        res = run(trip_type="법인카드", items=[
            {"field": "부서 회식", "amount": 150000, "merchant_type": "노래방", "payment": "법인카드"},
        ])
        self.assertEqual(find(res, "C-BANNED-MERCHANT")["verdict"], FIX)

    def test_weekend_use(self):
        res = run(trip_type="법인카드", items=[
            {"field": "다과 구입", "amount": 30000, "date": "2026-10-24", "payment": "법인카드"},  # 토요일
        ])
        self.assertEqual(find(res, "C-HOLIDAY")["verdict"], FIX)

    def test_card_late_settlement(self):
        res = run(trip_type="법인카드", settlement_date="2026-11-05", items=[
            {"field": "다과 구입", "amount": 30000, "date": "2026-10-20", "payment": "법인카드"},
        ])
        self.assertEqual(find(res, "C-LATE-SETTLEMENT")["verdict"], CHECK)

    def test_split_payment(self):
        res = run(trip_type="업무추진비", items=[
            {"field": "업무추진비", "amount": 300000, "date": "2026-10-22", "merchant": "OO식당",
             "payment": "법인카드", "attendees": 6},
            {"field": "업무추진비", "amount": 280000, "date": "2026-10-22", "merchant": "OO식당",
             "payment": "법인카드", "attendees": 6},
        ])
        self.assertEqual(find(res, "B-SPLIT-PAYMENT")["verdict"], FIX)

    def test_business_needs_counterpart(self):
        res = run(trip_type="업무추진비", items=[
            {"field": "업무추진비(유관기관 업무협의)", "amount": 120000, "date": "2026-10-22",
             "payment": "법인카드"},
        ])
        self.assertEqual(find(res, "B-COUNTERPART")["verdict"], FIX)

    def test_condolence_cap(self):
        res = run(trip_type="업무추진비", items=[{"field": "경조금", "amount": 100000, "payment": "현금"}])
        self.assertEqual(find(res, "B-CONDOLENCE-CAP")["verdict"], FIX)

    def test_receipt_draft_fields(self):
        """U-06 영수증 화면의 '지출 건 초안'을 그대로 넣어도 동작하는지 (purpose, business_type)"""
        draft = {"merchant": "OO호프", "business_type": "맥주전문점", "date": "2026-10-21",
                 "time": "23:40", "amount": 85000, "purpose": "회의비", "payment": "법인카드"}
        res = run(trip_type="법인카드", items=[draft])
        self.assertEqual(find(res, "C-OTHER-BAR")["verdict"], FIX)
        self.assertEqual(find(res, "C-ODD-HOURS")["verdict"], FIX)
        self.assertEqual(res["items"][0]["field"], "회의비")

    def test_empty_items_raises(self):
        with self.assertRaises(ValueError):
            verify_claim({"trip_type": "국내출장", "items": []})


if __name__ == "__main__":
    unittest.main()
