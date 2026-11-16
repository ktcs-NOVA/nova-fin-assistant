from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_optional_user
from app.core.db import get_db
from app.domains.receipt import service
from app.domains.receipt.schemas import ReceiptRequest, ReceiptResponse
from app.models import User

router = APIRouter(prefix="/api", tags=["U-06 영수증 인식"])


@router.post(
    "/receipt",
    response_model=ReceiptResponse,
    summary="영수증 사진 1장 → 가맹점·금액·일시·용도 후보 (공용 OpenAI 키로 판독)",
)
def receipt(
    req: ReceiptRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> dict:
    result = service.recognize(req)
    # 로그인한 사람이 올린 사진은 보관해 두고 번호를 돌려줌 → 정산 건의 증빙 사진으로 씀
    if user is not None:
        result["receipt_id"] = service.store(db, user, req, result)
    return result


@router.get("/receipts/{receipt_id}/image", summary="보관한 영수증 사진 (올린 본인 · 회계 관리자)")
def receipt_image(
    receipt_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    path, media_type = service.image_file(db, user, receipt_id)
    return FileResponse(path, media_type=media_type)
