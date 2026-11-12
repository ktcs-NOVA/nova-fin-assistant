"""시연용 관리자 검토함 데이터 적재 — 출장 27건 (팀원 2026-11-10 패키지 '개발연동_정산') + 점심·회식·회의비 17건 (종원 2026-11-12).

    uv run python -m scripts.seed_demo          # 적재 (이미 들어간 건은 건너뜀)
    uv run python -m scripts.seed_demo --reset  # 시연 건만 지우고 다시 적재

먼저 `uv run python -m scripts.seed` (계정 5개 + S-2026-001) 를 돌려 두세요.
데이터는 scripts/data/demo_submissions.json (출장) 과 demo_meet_cases.json (점심·회식·회의비). 인명·부서·금액 전부 가상.
AI 판정은 U-04 엔진이 실제로 낸 결과를 저장합니다. 엑셀의 기대 판정과 다른 건은 끝에 표로 보여 주므로
엔진을 고친 뒤 --reset 으로 다시 적재하면 됩니다.
"""

import json
import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.constants import ROLE_EMPLOYEE
from app.core.db import SessionLocal
from app.core.errors import AppError
from app.domains.submissions import service as subs
from app.models import Expense, User

KST = ZoneInfo("Asia/Seoul")
DATA = Path(__file__).with_name("data") / "demo_submissions.json"
DATA_MEET = Path(__file__).with_name("data") / "demo_meet_cases.json"
EMPLOYEE_NO_PREFIX = "D"  # D3001~: 시연용 가상 직원. 로그인 화면 계정(E/A)과 섞이지 않게 접두사 분리
DEFAULT_ACCOUNT = "여비교통비"  # 출장 여비는 모두 여비교통비. M-05 비교는 AI 제안과 일치하는 상태로 시작


def purpose_of(c: dict) -> str:
    if c["field"] == "근무지 내 교통비":
        return f"{c['destination']} 근무지 내 출장 교통비"
    return f"{c['destination']} 출장 {c['field']} 정산"


def build_request(c: dict) -> dict:
    """JSON 한 건 → POST /api/submissions 요청 모양 (직원이 제출한 것과 같은 경로로 넣기 위해)."""
    j = c["inputs"]
    local = c["field"] == "근무지 내 교통비"
    trip = {
        "start_date": c["start"], "end_date": c["end"],
        "region": c["region"] or c["destination"],
        "settlement_date": c["claim_date"],  # 정산 기한 검사용
    }
    if c["field"] == "자가용 교통비" or j.get("transport") == "자가용":
        trip["vehicle"] = "자가용"
        trip["private_car_approved"] = bool(j.get("approval_verified"))
    else:
        trip["vehicle"] = j.get("vehicle") or "대중교통"
    if local:
        trip["hours"] = j.get("hours")
        trip["round_trip_km"] = j.get("round_trip_km")

    item = {
        "field": c["field"], "amount": c["amount"], "date": c["start"], "note": c["remark"],
        "payment": "법인카드" if c["has_receipt"] else "여비 지급",
        "receipt": c["has_receipt"], "case_id": c["case_id"],
    }
    if c["nights"]:
        item["nights"] = c["nights"]
    if j.get("seat_class"):
        item["seat_class"] = j["seat_class"]
    if j.get("breakfast_included"):
        item["breakfast_included"] = True
    if j.get("free_meals"):
        item["meals_provided"] = int(j["free_meals"])
    if j.get("alternative_fare"):
        item["public_fare"] = int(j["alternative_fare"])

    req = {
        "trip_type": "근무지 내 출장" if local else "국내출장",
        "grade": c["grade"], "trip": trip, "items": [item],
        "purpose": purpose_of(c), "account": DEFAULT_ACCOUNT,
    }
    if j.get("distance_km"):
        req["private_car"] = {
            "distance_km": j["distance_km"], "fuel": j.get("fuel_type"),
            "km_per_liter": j.get("efficiency_km_per_l"), "price_per_liter": j.get("unit_price"),
            "tolls": j.get("toll"), "public_fare": j.get("alternative_fare"),
        }
    return req


# 예산항목 → 청구 유형·엔진 분류·계정과목. 미확정은 계정을 비워 M-05 비교 카드에 "(없음)" 으로 보이게 둠
MEET_BUDGET = {
    "업무추진비": ("업무추진비", "business", "업무추진비"),
    "조직관리비": ("법인카드", "org", "조직관리비"),
    "미확정": ("법인카드", "general", None),
}


def build_meet_request(c: dict) -> dict:
    """점심·회식·회의비 JSON 한 건 → POST /api/submissions 요청 모양.

    1인당 한도는 미확보(NULL)라 엔진에 넘기지 않고, 참석 인원은 메모와 extra 로만 남깁니다 (유의사항 ①).
    """
    trip_type, category, account = MEET_BUDGET[c["budget_item"]]
    n = c.get("participants")
    note = f"{c['purpose']}" + (f" · 참석 {n}명" if n else " · 참석 인원 미기재")
    item = {
        "field": f"{c['expense_type']}", "amount": c["amount"], "date": c["date"], "time": c["time"],
        "merchant": c["merchant"], "merchant_type": c["merchant_type"], "payment": c["payment"],
        "note": note, "category": category, "receipt": c["has_receipt"], "case_id": c["case_id"],
        "participant_count": n, "budget_item": c["budget_item"],
    }
    if c["has_attendees"] and n:
        item["attendees"] = f"총 {n}명 (사용자·상대방 소속·직책·성명 기재)"
    if c["pre_approval"] == "있음":
        item["pre_approved"] = True
    if c["pre_approval"] == "예외서류 제출":
        item["reason_doc"] = True
    if c["daily_audit"] == "있음":
        item["daily_audit"] = True
    items = [item]
    if c.get("related_payment"):  # 같은 날·같은 가맹점 분리 결제 건 (BIZ-07 분할결제 의심)
        r = c["related_payment"]
        items.append({**item, "amount": r["amount"], "time": r["time"], "case_id": None,
                      "case_ref": c["case_id"], "note": note + " · 같은 간담회 2차 결제"})
    return {
        "trip_type": trip_type, "grade": c["grade"],
        "trip": {"settlement_date": c["claim_date"]},  # 법인카드 10일 결의 기한 검사용
        "items": items, "purpose": c["purpose"], "account": account,
    }


def find_case_expense(db, case_id: str) -> Expense | None:
    return db.scalar(select(Expense).where(Expense.extra["case_id"].astext == case_id))


def ensure_user(db, c: dict) -> User:
    user = db.scalar(select(User).where(User.name == c["submitter"], User.department == c["dept"]))
    if user:
        return user
    taken = db.scalars(select(User.employee_no).where(User.employee_no.like(f"{EMPLOYEE_NO_PREFIX}%"))).all()
    nums = [int(no[1:]) for no in taken if no[1:].isdigit()]
    user = User(
        employee_no=f"{EMPLOYEE_NO_PREFIX}{(max(nums) + 1) if nums else 3001}",
        name=c["submitter"], department=c["dept"], grade=c["grade"], role=ROLE_EMPLOYEE,
    )
    db.add(user)
    db.flush()
    return user


def reset(db, cases: list[dict]) -> int:
    n = 0
    for c in cases:
        e = find_case_expense(db, c["case_id"])
        if e is None:
            continue
        sub, trip = e.submission, e.trip
        for x in (sub.expenses if sub is not None else [e]):
            db.delete(x)
        if sub is not None:
            db.delete(sub)
        if trip is not None:
            db.delete(trip)
        n += 1
    db.flush()
    return n


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    batches = [
        (json.loads(DATA.read_text(encoding="utf-8"))["cases"], build_request),
        (json.loads(DATA_MEET.read_text(encoding="utf-8"))["cases"], build_meet_request),
    ]
    cases = [c for group, _ in batches for c in group]
    with SessionLocal() as db:
        if "--reset" in sys.argv:
            print(f"시연 건 {reset(db, cases)}건 삭제")
        added, skipped, mismatch = 0, 0, []
        for c, build in [(c, build) for group, build in batches for c in group]:
            if find_case_expense(db, c["case_id"]) is not None:
                skipped += 1
                continue
            user = ensure_user(db, c)
            try:
                sub = subs.create_submission(db, user, build(c))
            except AppError as e:
                print(f"  ! {c['case_id']} 적재 실패: {e.message}")
                continue
            # 제출일은 엑셀의 정산 제출일로 (create_submission 은 지금 시각을 넣음)
            sub.submitted_at = datetime.combine(datetime.fromisoformat(c["claim_date"]).date(), time(9, 0), tzinfo=KST)
            added += 1
            if sub.verdict != c["expected_verdict"]:
                mismatch.append((c["case_id"], sub.code, c["rule"], c["expected_verdict"], sub.verdict))
        db.commit()
    print(f"적재 {added}건, 건너뜀 {skipped}건 (총 {len(cases)}건)")
    if mismatch:
        print("\n엑셀 기대 판정과 엔진 판정이 다른 건 (엔진 결과를 저장했음):")
        for case_id, code, rule, exp, got in mismatch:
            print(f"  {case_id} {code} {rule:<18} 기대={exp}  엔진={got}")


if __name__ == "__main__":
    main()
