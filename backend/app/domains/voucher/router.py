from fastapi import APIRouter

from app.core.errors import AppError
from app.domains.voucher.schemas import VoucherDraftRequest, VoucherDraftResponse
from app.precheck import draft_voucher

router = APIRouter(prefix="/api", tags=["U-07 결의서 초안"])


@router.post(
    "/voucher-draft",
    response_model=VoucherDraftResponse,
    summary="청구 내역 → 지출결의서 초안 (적요 · 계정과목 · 첨부서류 · 제출 기한)",
)
def voucher_draft(req: VoucherDraftRequest) -> dict:
    try:
        return draft_voucher(req.model_dump())
    except ValueError as e:
        raise AppError(str(e), 400) from e
