from fastapi import APIRouter

from app.domains.procedure import service
from app.domains.procedure.schemas import ProcedureRequest, ProcedureResponse

router = APIRouter(prefix="/api", tags=["U-02 업무절차 안내"])


@router.post(
    "/procedure",
    response_model=ProcedureResponse,
    summary="업무 → 필요 서류 · 작성 순서 · 기한 · 결재자",
)
def procedure(req: ProcedureRequest) -> dict:
    return service.get_procedure(req.task)
