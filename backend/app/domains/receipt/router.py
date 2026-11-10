from fastapi import APIRouter

from app.domains.receipt import service
from app.domains.receipt.schemas import ReceiptRequest, ReceiptResponse

router = APIRouter(prefix="/api", tags=["U-06 영수증 인식"])


@router.post(
    "/receipt",
    response_model=ReceiptResponse,
    summary="영수증 사진 1장 → 가맹점·금액·일시·용도 후보 (공용 OpenAI 키로 판독)",
)
def receipt(req: ReceiptRequest) -> dict:
    return service.recognize(req)
