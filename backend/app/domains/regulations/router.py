from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_optional_user
from app.core.db import get_db
from app.core.errors import AppError
from app.domains.regulations import service
from app.domains.regulations.schemas import RegulationDetail, RegulationSummary
from app.models import User

router = APIRouter(prefix="/api/regulations", tags=["U-03 규정 원문"])


@router.get("", response_model=list[RegulationSummary], summary="원문으로 볼 수 있는 규정 목록")
def list_regulations(
    db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)
) -> list[dict]:
    return service.list_regulations(db, user.role if user else None)


@router.get(
    "/{doc_id}", response_model=RegulationDetail, summary="규정 원문 (조문·별표를 원래 순서대로)"
)
def get_regulation(
    doc_id: int, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)
) -> dict:
    found = service.get_regulation(db, doc_id, user.role if user else None)
    if found is None:
        raise AppError("규정을 찾을 수 없습니다.", 404)
    return found
