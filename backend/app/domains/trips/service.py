"""출장 신청: 출장을 정산 전에 미리 등록하고, 정산할 때 그 값을 그대로 이어 씁니다.

진행 단계(stage)는 저장하지 않고 날짜와 정산 연결 여부로 매번 계산합니다.
실제 결재는 하지 않으므로 신청하면 바로 '신청' 상태입니다.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Submission, Trip, User

KST = ZoneInfo("Asia/Seoul")
REQUESTED = "신청"
CANCELED = "취소"


def today() -> date:
    return datetime.now(KST).date()


METROS = ("부산", "대구", "인천", "광주", "대전", "울산")


def region_of(address: str | None) -> str | None:
    """출장지 → 숙박비 상한용 지역 구분. 모르면 None.

    경로 조회 결과는 '부산역 (부산광역시 동구 중앙대로 206)' 처럼 이름 뒤 괄호에 주소가 붙으므로
    낱말 전체를 훑습니다. '광주'는 경기도 광주시와 헷갈리므로 '광주광역시'로 적힌 경우만 광역시로 봅니다.
    """
    words = [w.strip("()[],·") for w in (address or "").split()]
    words = [w for w in words if w]
    if not words:
        return None
    if any(w.startswith("서울") for w in words):
        return "서울"
    if any(w.endswith("광역시") for w in words):
        return "광역시"
    if any(w.startswith(m) and m != "광주" for w in words for m in METROS):
        return "광역시"
    return "기타"


def stage_of(trip: Trip, sub: Submission | None, on: date) -> str:
    if trip.status == CANCELED:
        return "취소"
    if sub is not None:
        return "정산 제출"
    if on < trip.start_date:
        return "출장 예정"
    if on <= trip.end_date:
        return "출장 중"
    return "정산 전"


def _latest_submissions(db: Session, trip_ids: list[int]) -> dict[int, Submission]:
    if not trip_ids:
        return {}
    rows = db.scalars(
        select(Submission).where(Submission.trip_id.in_(trip_ids)).order_by(Submission.id)
    )
    return {s.trip_id: s for s in rows}  # 같은 출장에 여러 번 냈으면(재제출) 마지막 것


def view(trip: Trip, sub: Submission | None, on: date | None = None) -> dict:
    return {
        "id": trip.id,
        "trip_type": trip.trip_type or "국내출장",
        "purpose": trip.title,
        "destination": trip.destination,
        "region": trip.region,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "vehicle": trip.vehicle,
        "private_car_approved": trip.private_car_approved,
        "distance_km": trip.distance_km,
        "education": bool(trip.education),
        "hours": trip.hours,
        "start_time": trip.start_time,
        "end_time": trip.end_time,
        "companions": trip.companions or [],
        "status": trip.status or REQUESTED,
        "stage": stage_of(trip, sub, on or today()),
        "submission": (
            {"id": sub.code, "status": sub.status, "verdict": sub.verdict}
            if sub is not None
            else None
        ),
    }


def create_trip(db: Session, user: User, req: dict) -> dict:
    destination = (req.get("destination") or "").strip() or None
    trip = Trip(
        user=user,
        trip_type=req.get("trip_type") or "국내출장",
        title=req["purpose"].strip(),
        destination=destination,
        region=req.get("region") or region_of(destination),
        start_date=req["start_date"],
        end_date=req["end_date"],
        vehicle=req.get("vehicle") or "대중교통",
        private_car_approved=bool(req.get("private_car_approved")),
        distance_km=req.get("distance_km"),
        education=bool(req.get("education")),
        hours=req.get("hours"),
        start_time=req.get("start_time"),
        end_time=req.get("end_time"),
        companions=[
            {"name": c["name"].strip(), "dept": (c.get("dept") or "").strip()}
            for c in req.get("companions") or []
            if c.get("name", "").strip()
        ]
        or None,
        status=REQUESTED,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return view(trip, None)


def list_trips(db: Session, user: User) -> list[dict]:
    """내가 신청한 출장 (취소한 것 제외). 가까운 일정이 위로 오도록 시작일 순."""
    trips = list(
        db.scalars(
            select(Trip)
            .where(Trip.user_id == user.id, Trip.status == REQUESTED)
            .order_by(Trip.start_date.desc(), Trip.id.desc())
        )
    )
    subs = _latest_submissions(db, [t.id for t in trips])
    on = today()
    return [view(t, subs.get(t.id), on) for t in trips]


def own_trip(db: Session, user: User, trip_id: int) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None or trip.user_id != user.id or trip.status is None:
        raise AppError("출장 신청을 찾을 수 없습니다.", 404)
    return trip


def get_trip(db: Session, user: User, trip_id: int) -> dict:
    trip = own_trip(db, user, trip_id)
    return view(trip, _latest_submissions(db, [trip.id]).get(trip.id))


def cancel_trip(db: Session, user: User, trip_id: int) -> None:
    trip = own_trip(db, user, trip_id)
    if _latest_submissions(db, [trip.id]):
        raise AppError("이미 정산을 낸 출장은 취소할 수 없습니다.", 409)
    trip.status = CANCELED
    db.commit()
