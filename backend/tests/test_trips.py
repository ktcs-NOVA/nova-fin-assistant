"""출장 신청 → 정산 연결. 단위 테스트는 DB 없이, API 테스트는 DB·시드가 있어야 하고 아니면 건너뜁니다."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.core.db import SessionLocal
from app.core.security import create_token
from app.domains.trips.service import region_of, stage_of
from app.main import app
from app.models import Submission, Trip, User

client = TestClient(app)
D = date(2026, 12, 3)


def auth(employee_no: str) -> dict:
    return {"Authorization": f"Bearer {create_token(employee_no)}"}


def test_region_from_address():
    assert region_of("서울특별시 중구 세종대로 110") == "서울"
    assert region_of("부산광역시 해운대구 마린시티2로 38") == "광역시"
    assert region_of("대전 서구 둔산로 100") == "광역시"
    assert region_of("세종특별자치시 한누리대로 2130") == "기타"
    assert region_of("경기도 수원시") == "기타"
    assert region_of("") is None and region_of(None) is None


def test_stage_by_date_and_settlement():
    trip = Trip(start_date=D, end_date=D + timedelta(days=1), status="신청")
    assert stage_of(trip, None, D - timedelta(days=1)) == "출장 예정"
    assert stage_of(trip, None, D) == "출장 중"
    assert stage_of(trip, None, D + timedelta(days=1)) == "출장 중"
    assert stage_of(trip, None, D + timedelta(days=2)) == "정산 전"
    assert stage_of(trip, Submission(), D + timedelta(days=2)) == "정산 제출"
    trip.status = "취소"
    assert stage_of(trip, None, D) == "취소"


@pytest.fixture
def made():
    try:
        with SessionLocal() as db:
            if db.scalar(select(User).where(User.employee_no == "E1001")) is None:
                pytest.skip("시드 전")
    except OperationalError:
        pytest.skip("DB 꺼짐")
    ids = {"trips": [], "subs": []}
    yield ids
    with SessionLocal() as db:
        for sub in db.scalars(select(Submission).where(Submission.code.in_(ids["subs"]))):
            for e in list(sub.expenses):
                db.delete(e)
            db.delete(sub)
        db.flush()
        for t in db.scalars(select(Trip).where(Trip.id.in_(ids["trips"]))):
            for e in list(t.expenses):
                db.delete(e)
            db.delete(t)
        db.commit()


def request_trip(made, **over) -> dict:
    body = {
        "purpose": "테스트 선사 방문",
        "destination": "부산광역시 강서구 신항로 1",
        "start_date": "2026-10-20",
        "end_date": "2026-10-21",
        "distance_km": 330.5,
        **over,
    }
    r = client.post("/api/trips", json=body, headers=auth("E1001"))
    assert r.status_code == 201, r.text
    made["trips"].append(r.json()["id"])
    return r.json()


def test_request_then_settle_links_same_trip(made):
    trip = request_trip(made, education=True)
    assert trip["region"] == "광역시" and trip["status"] == "신청"
    assert trip["education"] is True and trip["hours"] is None
    assert trip["stage"] == "정산 전"  # 지난 날짜라 다녀온 출장
    assert any(
        t["id"] == trip["id"] for t in client.get("/api/trips", headers=auth("E1001")).json()
    )

    claim = {
        "trip_type": "국내출장",
        "grade": "직원 3급 이하",
        "trip_id": trip["id"],
        "trip": {"start_date": "2026-10-20", "end_date": "2026-10-21", "region": "광역시"},
        "items": [
            {"field": "철도운임", "amount": 59800, "date": "2026-10-20", "seat_class": "일반"}
        ],
    }
    r = client.post("/api/submissions", json=claim, headers=auth("E1001"))
    assert r.status_code == 201, r.text
    sub = r.json()
    made["subs"].append(sub["id"])
    assert sub["purpose"] == "테스트 선사 방문"  # 건명을 안 적으면 신청한 목적
    assert sub["trip"]["destination"] == "부산광역시 강서구 신항로 1"  # 출장보고서 출장지로 이어짐

    after = client.get(f"/api/trips/{trip['id']}", headers=auth("E1001")).json()
    assert after["stage"] == "정산 제출" and after["submission"]["id"] == sub["id"]
    assert client.delete(f"/api/trips/{trip['id']}", headers=auth("E1001")).status_code == 409


def test_cancel_and_ownership(made):
    trip = request_trip(made, start_date="2099-01-01", end_date="2099-01-01")
    assert trip["stage"] == "출장 예정"
    assert client.get(f"/api/trips/{trip['id']}", headers=auth("E1002")).status_code == 404
    assert client.delete(f"/api/trips/{trip['id']}", headers=auth("E1001")).status_code == 204
    ids = [t["id"] for t in client.get("/api/trips", headers=auth("E1001")).json()]
    assert trip["id"] not in ids


def test_end_before_start_is_rejected(made):
    r = client.post(
        "/api/trips",
        json={"purpose": "x", "start_date": "2026-10-21", "end_date": "2026-10-20"},
        headers=auth("E1001"),
    )
    assert r.status_code == 422 or r.status_code == 400
