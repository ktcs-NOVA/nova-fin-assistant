"""
U-05 출장비 계산 테스트.

실행 (backend 폴더에서):
    python -m unittest discover -s app/precheck/tests -t . -v
"""

import unittest

from app.precheck import calc_travel, verify_claim
from app.precheck.rules import OK, CHECK


def line(res, field):
    hits = [l for l in res["lines"] if l["field"] == field]
    assert hits, f"{field} 줄이 없습니다: {[l['field'] for l in res['lines']]}"
    return hits[0]


class TravelCalc(unittest.TestCase):

    def test_busan_1night_with_breakfast(self):
        """시연 시나리오: 직원 3급, 부산 1박 2일, 조식 포함"""
        res = calc_travel({"grade": "직원 3급 이하",
                           "trip": {"start_date": "2026-10-20", "end_date": "2026-10-21",
                                    "region": "부산", "breakfast_nights": 1},
                           "fares": [{"type": "철도", "amount": 59800, "seat_class": "일반"}]})
        self.assertEqual(res["days"], 2)
        self.assertEqual(res["nights"], 1)
        self.assertEqual(line(res, "일비")["amount"], 60000)
        self.assertEqual(line(res, "식비")["amount"], 45000)          # 54,000 - 9,000
        self.assertEqual(line(res, "숙박비")["amount"], 90000)        # 광역시 상한
        self.assertIn("117,000원", line(res, "숙박비")["note"])       # 30% 추가 한도
        self.assertEqual(res["summary"]["estimated_max"], 60000 + 45000 + 90000 + 59800)

    def test_seoul_grade2_rate(self):
        res = calc_travel({"grade": "직원 2급",
                           "trip": {"start_date": "2026-11-10", "end_date": "2026-11-12", "region": "서울"}})
        self.assertEqual(line(res, "숙박비")["amount"], 200000)       # 100,000 × 2박
        self.assertEqual(line(res, "식비")["amount"], 81000)          # 27,000 × 3일

    def test_company_car_half_per_diem(self):
        res = calc_travel({"trip": {"start_date": "2026-10-20", "end_date": "2026-10-20",
                                    "region": "기타", "vehicle": "업무용차량"}})
        self.assertEqual(line(res, "일비")["amount"], 15000)
        self.assertNotIn("숙박비", [l["field"] for l in res["lines"]])   # 당일 출장

    def test_education_trip_per_diem_2days(self):
        res = calc_travel({"trip": {"start_date": "2026-10-19", "end_date": "2026-10-23",
                                    "region": "기타", "purpose": "교육"}})
        self.assertEqual(line(res, "일비")["amount"], 60000)          # 5일이지만 2일 한도

    def test_long_stay_reduction(self):
        """도착 다음날부터 15일 초과분 1할, 30일 초과분 3할 감액 (총 35일)"""
        res = calc_travel({"trip": {"start_date": "2026-10-01", "end_date": "2026-11-04", "region": "기타"}})
        # 도착일 + 다음날부터 15일 = 16일 정액, 16~30일째 15일 × 0.9, 31~34일째 4일 × 0.7
        expected = 30000 * 16 + 30000 * 0.9 * 15 + 30000 * 0.7 * 4
        self.assertEqual(line(res, "일비")["amount"], int(round(expected)))

    def test_meals_provided(self):
        res = calc_travel({"trip": {"start_date": "2026-10-20", "end_date": "2026-10-20", "meals_provided": 1}})
        self.assertEqual(line(res, "식비")["amount"], 18000)

    def test_lodging_provided(self):
        res = calc_travel({"trip": {"start_date": "2026-10-20", "end_date": "2026-10-21",
                                    "region": "서울", "lodging_provided": True}})
        self.assertEqual(line(res, "숙박비")["amount"], 0)

    def test_executive_lodging_actual(self):
        res = calc_travel({"grade": "본부장",
                           "trip": {"start_date": "2026-10-20", "end_date": "2026-10-21", "region": "서울"}})
        self.assertIsNone(line(res, "숙박비")["amount"])
        self.assertEqual(line(res, "숙박비")["type"], "실비")

    def test_private_car_capped_by_public_fare(self):
        res = calc_travel({"trip": {"start_date": "2026-10-20", "end_date": "2026-10-20", "vehicle": "자가용"},
                           "private_car": {"distance_km": 400, "km_per_liter": 10, "price_per_liter": 1700,
                                           "tolls": 20000, "public_fare": 70000}})
        # 400 ÷ 10 × 1,700 + 20,000 = 88,000 → 운임 70,000 한도
        self.assertEqual(line(res, "교통비(자가용)")["amount"], 70000)

    def test_private_car_under_fare(self):
        res = calc_travel({"trip": {"vehicle": "자가용"},
                           "private_car": {"distance_km": 100, "km_per_liter": 12.5, "price_per_liter": 1600,
                                           "public_fare": 30000}})
        self.assertEqual(line(res, "교통비(자가용)")["amount"], 12800)

    def test_intra_city(self):
        res = calc_travel({"trip_type": "근무지 내 출장", "trip": {"hours": 5}})
        self.assertEqual(line(res, "교통비")["amount"], 30000)
        self.assertEqual(len(res["lines"]), 1)

    def test_roundtrip_into_verify_is_ok(self):
        """계산 결과를 그대로 U-04에 넣으면 '규정상 확인 가능'이어야 함"""
        res = calc_travel({"grade": "직원 3급 이하",
                           "trip": {"start_date": "2026-10-20", "end_date": "2026-10-21",
                                    "region": "부산", "breakfast_nights": 1},
                           "fares": [{"type": "철도", "amount": 59800, "seat_class": "일반"}]})
        checked = verify_claim(res["verify_request"])
        self.assertEqual(checked["overall"], OK, checked)

    def test_roundtrip_private_car_needs_approval(self):
        res = calc_travel({"trip": {"start_date": "2026-10-20", "end_date": "2026-10-20", "vehicle": "자가용"},
                           "private_car": {"distance_km": 100, "public_fare": 30000}})
        checked = verify_claim(res["verify_request"])
        self.assertEqual(checked["overall"], CHECK)


if __name__ == "__main__":
    unittest.main()
