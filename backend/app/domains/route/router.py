from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.domains.route import service
from app.models import User

router = APIRouter(prefix="/api", tags=["U-05 경로 조회"])


class RouteRequest(BaseModel):
    destination: str = Field(max_length=200, examples=["부산광역시 중구 중앙대로 120"])


class RouteResponse(BaseModel):
    destination: str  # 찾은 도착지 (도로명 주소, 장소 이름으로 찾았으면 '이름 (주소)')
    distance_km: float  # 근무지 → 도착지 편도 자동차 거리
    duration_min: int  # 예상 소요 시간


@router.post(
    "/route",
    response_model=RouteResponse,
    summary="근무지(공사 본사) → 도착지 자동차 거리 (네이버 지도)",
)
def route(req: RouteRequest, _user: User = Depends(get_current_user)) -> dict:
    # 바깥 API(무료 사용량 있음)를 부르므로 로그인한 사람만
    return service.lookup(req.destination)
