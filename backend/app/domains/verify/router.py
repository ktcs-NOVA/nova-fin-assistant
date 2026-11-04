from fastapi import APIRouter

from app.domains.verify import service
from app.domains.verify.schemas import VerifyRequest, VerifyResponse

router = APIRouter(prefix="/api", tags=["U-04 청구 검증"])


@router.post(
    "/verify", response_model=VerifyResponse, summary="청구 내역 → 항목별 판정 + 근거 + 수정 방법"
)
def verify(req: VerifyRequest) -> dict:
    return service.verify(req.model_dump())
