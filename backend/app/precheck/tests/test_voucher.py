"""
U-07 결의서 초안 테스트.

실행 (backend 폴더에서):
    python -m unittest discover -s precheck/tests -t . -v
"""

import unittest
from datetime import date

from app.precheck import calc_travel, draft_voucher, suggest_account

TODAY = date(2026, 10, 23)


def names(draft):
    return [a["name"] for a in draft["attachments"]]


class VoucherDraft(unittest.TestCase):

    def busan(self):
        c = calc_travel({"grade": "직원 3급 이하",
                         "trip": {"start_date": "2026-10-20", "end_date": "2026-10-21",
                                  "region": "부산", "breakfast_nights": 1},
                         "fares": [{"type": "철도", "amount": 59800, "seat_class": "일반"}]})
        req = c["verify_request"]
        req["requester"] = {"name": "홍길동", "department": "해운정책팀"}
        return draft_voucher(req, today=TODAY)

    def test_travel_draft_from_calc(self):
        d = self.busan()
        self.assertEqual(d["status"], "제출 가능")
        self.assertEqual(d["header"]["total"], 254800)
        self.assertEqual(d["header"]["title"], "부산 출장 여비 정산(2026-10-20~2026-10-21)")
        self.assertTrue(all(l["account"] == "여비교통비" for l in d["lines"]))
        self.assertIn("숙박비 90,000원(1박, 조식 포함)", d["summary"])
        self.assertIn("출장원(정산) — 여비규정 별지 제3호", names(d))
        self.assertIn("출장보고서 — 여비규정 별지 제4호", names(d))
        self.assertEqual(d["deadlines"][0]["due"], "2026-11-05")
        self.assertEqual(d["warnings"], [])

    def test_fix_items_block_submission(self):
        d = draft_voucher({"trip_type": "국내출장", "grade": "직원 3급 이하",
                           "trip": {"start_date": "2026-10-20", "end_date": "2026-10-21", "region": "기타"},
                           "items": [{"field": "철도운임", "amount": 70000, "seat_class": "특실"}]}, today=TODAY)
        self.assertEqual(d["status"], "제출 전 보완 필요")
        self.assertTrue(any("보완 필요" in w for w in d["warnings"]))

    def test_card_meeting_late_night(self):
        d = draft_voucher({"trip_type": "법인카드",
                           "items": [{"field": "회의 식대", "amount": 80000, "date": "2026-10-21",
                                      "time": "23:30", "payment": "법인카드", "merchant": "OO식당"}]},
                          today=TODAY)
        self.assertEqual(d["lines"][0]["account"], "조직관리비")
        self.assertIn("법인카드 사용내역 — 법인카드 지침 별지 제6호", names(d))
        self.assertIn("사유서 — 법인카드 지침 별지 제5호", names(d))
        self.assertEqual(d["deadlines"][0]["due"], "2026-10-31")
        self.assertEqual(d["header"]["payee"], "OO식당")

    def test_business_over_500k(self):
        d = draft_voucher({"trip_type": "업무추진비",
                           "items": [{"field": "업무추진비(간담회)", "amount": 620000, "date": "2026-10-22",
                                      "payment": "법인카드", "attendees": ["해양수산부 OOO 과장"],
                                      "pre_approved": True}]}, today=TODAY)
        self.assertEqual(d["lines"][0]["account"], "업무추진비")
        self.assertIn("업무추진비 사전결재 문서 — 업무추진비 지침 별지 제1호", names(d))
        self.assertIn("참석자 명단(상대방 소속·직책·성명, 총인원)", names(d))

    def test_receipt_draft_input(self):
        """U-06 영수증 초안을 그대로 넣어도 결의서가 만들어지는지"""
        d = draft_voucher({"trip_type": "법인카드",
                           "items": [{"merchant": "OO문구", "business_type": "문구점", "date": "2026-10-21",
                                      "time": "14:00", "amount": 23000, "purpose": "사무용품",
                                      "payment": "법인카드"}]}, today=TODAY)
        self.assertEqual(d["lines"][0]["account"], "소모품비")
        self.assertEqual(d["lines"][0]["confidence"], "가정")
        self.assertTrue(any("가정값" in w for w in d["warnings"]))

    def test_unknown_account(self):
        acc = suggest_account({"field": "기타", "amount": 10000}, is_travel=False)
        self.assertEqual(acc["account"], "담당자 확인")

    def test_meal_outside_trip_is_org(self):
        acc = suggest_account({"field": "식비", "amount": 30000}, is_travel=False)
        self.assertEqual(acc["account"], "조직관리비")

    def test_grouping_same_account(self):
        d = draft_voucher({"trip_type": "법인카드",
                           "items": [{"field": "다과 구입", "amount": 20000, "date": "2026-10-21", "payment": "법인카드"},
                                     {"field": "회의 다과", "amount": 15000, "date": "2026-10-21", "payment": "법인카드"}]},
                          today=TODAY)
        self.assertEqual(len(d["lines"]), 1)
        self.assertEqual(d["lines"][0]["amount"], 35000)


class ReasonForm(unittest.TestCase):
    """철도·버스 증빙 곤란 시 사유서(결재문서) 템플릿 — 실무자 의견 반영"""

    def ktx(self, **extra):
        item = {"field": "철도운임", "amount": 59800, "seat_class": "일반", "receipt": False,
                "route": "서울역 → 부산역", **extra}
        return {"trip_type": "국내출장", "grade": "직원 3급 이하",
                "trip": {"start_date": "2026-10-20", "end_date": "2026-10-21", "region": "부산"},
                "requester": {"name": "홍길동", "department": "해운정책팀"},
                "items": [item]}

    def test_missing_ktx_receipt_gives_template(self):
        d = draft_voucher(self.ktx(), today=TODAY)
        self.assertEqual(d["status"], "제출 전 보완 필요")
        self.assertEqual(len(d["reason_forms"]), 1)
        form = d["reason_forms"][0]
        self.assertEqual(form["status"], "작성 필요")
        fields = {f["key"]: f for f in form["fields"]}
        self.assertEqual(fields["route"]["value"], "서울역 → 부산역")
        self.assertEqual(fields["mode"]["value"], "철도운임 (일반)")
        self.assertEqual(fields["reason"]["value"], "")          # 비어 있으면 화면이 흐린 예시 표시
        self.assertTrue(fields["reason"]["placeholder"].startswith("예:"))
        self.assertIn("증빙 대체 결재문서(사유서 · 부서장 승인)", names(d))

    def test_approved_substitute_within_fare_passes(self):
        d = draft_voucher(self.ktx(substitute_approved=True, authorized_fare=59800,
                                   no_receipt_reason="현장 현금 발권 후 승차권 분실"), today=TODAY)
        self.assertEqual(d["verify"]["fix"], 0)
        self.assertEqual(d["reason_forms"][0]["status"], "부서장 승인 완료")

    def test_approved_substitute_over_fare_is_fix(self):
        d = draft_voucher(self.ktx(substitute_approved=True, authorized_fare=50000), today=TODAY)
        self.assertEqual(d["verify"]["fix"], 1)

    def test_no_template_when_receipt_present(self):
        d = draft_voucher(self.ktx(receipt=True), today=TODAY)
        self.assertEqual(d["reason_forms"], [])

    def test_taxi_has_no_template(self):
        req = self.ktx()
        req["items"] = [{"field": "택시비", "amount": 12000, "receipt": False}]
        self.assertEqual(draft_voucher(req, today=TODAY)["reason_forms"], [])


if __name__ == "__main__":
    unittest.main()
