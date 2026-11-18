from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.domains.route import service
from app.models import User

router = APIRouter(prefix="/api", tags=["U-05 경로 조회"])


class RouteRequest(BaseModel):
    destination: str = Field(max_length=200, description="도착지 주소 또는 장소 이름")


class RouteResponse(BaseModel):
    destination: str  # 찾은 주소 (장소 이름으로 찾았으면 "이름 (주소)")
    distance_km: float  # 편도 거리
    duration_min: int


@router.post("/route", response_model=RouteResponse, summary="회사 → 도착지 자동차 경로 거리 (네이버 지도)")
def route(req: RouteRequest, user: User = Depends(get_current_user)) -> dict:
    return service.lookup(req.destination)
