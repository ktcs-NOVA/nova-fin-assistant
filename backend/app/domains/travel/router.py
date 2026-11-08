from fastapi import APIRouter

from app.core.errors import AppError
from app.domains.travel.schemas import TravelCalcRequest, TravelCalcResponse
from app.precheck import calc_travel

router = APIRouter(prefix="/api", tags=["U-05 출장비 계산"])


@router.post(
    "/travel-calc",
    response_model=TravelCalcResponse,
    summary="출장 정보 → 받을 수 있는 금액 (항목별 계산식 + 근거 조항)",
)
def travel_calc(req: TravelCalcRequest) -> dict:
    try:
        return calc_travel(req.model_dump())
    except ValueError as e:  # 엔진이 입력 오류를 ValueError 로 알려줌
        raise AppError(str(e), 400) from e
