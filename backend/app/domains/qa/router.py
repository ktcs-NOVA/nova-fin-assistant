from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.domains.qa import service
from app.domains.qa.schemas import QaRequest, QaResponse

router = APIRouter(prefix="/api", tags=["U-01 규정 Q&A"])


@router.post(
    "/qa",
    response_model=QaResponse,
    summary="질문 → 규정 답변, 절차 안내, 되묻기 중 하나 (챗봇이 도구를 고름)",
)
def ask(req: QaRequest, db: Session = Depends(get_db)) -> QaResponse:
    return service.ask(db, req.question)
