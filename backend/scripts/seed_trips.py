"""시연용 출장 신청 1건 — 홈 '내 출장'에 '정산 전' 출장이 보이도록 (노은비 E1001).

    uv run python -m scripts.seed_trips          # 적재 (이미 있으면 건너뜀)
    uv run python -m scripts.seed_trips --reset  # 시연 출장만 지우고 오늘 날짜 기준으로 다시 적재

날짜는 '오늘' 기준 지난주 월·화(1박 2일)로 잡아서 항상 '정산 전' 입니다. 시연에서는
홈 '내 출장' → 정산하기 → 신청 값이 잠긴 채 정산 → 출장보고서 순서로 보여 주면 됩니다.
시연 당일 아침에 --reset 으로 한 번 돌리면 날짜가 맞습니다.
먼저 `uv run python -m scripts.seed` (계정) 를 돌려 두세요. 장소는 시연용 예시입니다.
"""

import sys
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.db import SessionLocal
from app.domains.trips import service as trips
from app.models import Submission, Trip, User
from app.models.work_document import WorkDocument

KST = ZoneInfo("Asia/Seoul")
EMPLOYEE = "E1001"
PURPOSE = "서울 선사 간담회 (친환경 선박 금융 수요 조사)"


def demo_trip(today: date) -> dict:
    monday = today - timedelta(days=today.weekday() + 7)  # 지난주 월요일
    return {
        "purpose": PURPOSE,
        "destination": "서울특별시 영등포구 여의대로 108",
        "start_date": monday,
        "end_date": monday + timedelta(days=1),
        "start_time": time(8, 0),
        "end_time": time(18, 0),
        "vehicle": "대중교통",
        "distance_km": 390,
    }


def remove(db, user: User) -> int:
    """시연 출장과 거기 붙은 정산·서류를 지움 (직접 만든 다른 출장은 그대로)."""
    rows = db.scalars(
        select(Trip).where(Trip.user_id == user.id, Trip.status.is_not(None), Trip.title == PURPOSE)
    ).all()
    for trip in rows:
        for sub in db.scalars(select(Submission).where(Submission.trip_id == trip.id)).all():
            for doc in db.scalars(
                select(WorkDocument).where(WorkDocument.submission_id == sub.id)
            ).all():
                db.delete(doc)
            for e in list(sub.expenses):
                db.delete(e)
            db.delete(sub)
        db.flush()
        for e in list(trip.expenses):
            db.delete(e)
        db.delete(trip)
    db.flush()
    return len(rows)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.employee_no == EMPLOYEE))
        if user is None:
            print("계정이 없습니다. 먼저 `uv run python -m scripts.seed` 를 돌려 주세요.")
            return
        if "--reset" in sys.argv:
            print(f"시연 출장 {remove(db, user)}건 삭제")
        elif db.scalar(select(Trip).where(Trip.user_id == user.id, Trip.title == PURPOSE)):
            print(
                "시연 출장이 이미 있어요. 날짜를 오늘 기준으로 다시 잡으려면 --reset 을 붙이세요."
            )
            return
        view = trips.create_trip(db, user, demo_trip(datetime.now(KST).date()))
        print(f"  {view['stage']} · {view['purpose']} ({view['start_date']} ~ {view['end_date']})")
    print("완료 — 홈 '내 출장'에서 확인하세요.")


if __name__ == "__main__":
    main()
