from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.domains.trips import service
from app.domains.trips.schemas import TripCreate, TripView
from app.models import User

router = APIRouter(prefix="/api/trips", tags=["출장 신청"])


@router.post("", response_model=TripView, status_code=201, summary="출장 신청")
def create(req: TripCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.create_trip(db, user, req.model_dump())


@router.get("", response_model=list[TripView], summary="내 출장 목록 (진행 단계 포함)")
def list_mine(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.list_trips(db, user)


@router.get("/{trip_id}", response_model=TripView, summary="출장 신청 상세")
def detail(trip_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.get_trip(db, user, trip_id)


@router.delete("/{trip_id}", status_code=204, summary="출장 신청 취소 (정산 전만)")
def cancel(
    trip_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    service.cancel_trip(db, user, trip_id)
    return Response(status_code=204)
