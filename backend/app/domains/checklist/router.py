from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.domains.checklist import saved, service
from app.domains.checklist.schemas import (
    ChecklistResponse,
    SavedChecklist,
    SavedChecklistCreate,
    SavedChecklistItem,
    SavedChecklistItemUpdate,
)
from app.models import User

router = APIRouter(prefix="/api", tags=["체크리스트"])


@router.get("/checklist", response_model=ChecklistResponse, summary="경비 종류별 체크 항목")
def checklist(type: str = Query("국내출장", description="경비 종류")) -> dict:
    return service.get_checklist(type)


@router.get("/checklists", response_model=list[SavedChecklist], summary="내 체크리스트 목록")
def list_saved(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return saved.list_checklists(db, user)


@router.post(
    "/checklists",
    response_model=SavedChecklist,
    status_code=201,
    summary="절차 안내를 내 체크리스트로 저장",
)
def create_saved(
    req: SavedChecklistCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return saved.create_checklist(db, user, req.task)


@router.patch(
    "/checklists/{checklist_id}/items/{item_id}",
    response_model=SavedChecklistItem,
    summary="체크 항목 완료 표시",
)
def update_saved_item(
    checklist_id: int,
    item_id: int,
    req: SavedChecklistItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return saved.update_item(db, user, checklist_id, item_id, req.done)


@router.delete("/checklists/{checklist_id}", status_code=204, summary="내 체크리스트 삭제")
def delete_saved(
    checklist_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    saved.delete_checklist(db, user, checklist_id)
    return Response(status_code=204)
