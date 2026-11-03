from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.domains.qa import service
from app.domains.qa.schemas import QaRequest, QaResponse

router = APIRouter(prefix="/api", tags=["U-01 규정 Q&A"])


@router.post("/qa", response_model=QaResponse, summary="규정 질문 → 답변 + 근거 조항")
def ask(req: QaRequest, db: Session = Depends(get_db)) -> QaResponse:
    return service.answer_question(db, req.question)
