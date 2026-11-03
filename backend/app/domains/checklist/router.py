from fastapi import APIRouter, Query

from app.domains.checklist import service
from app.domains.checklist.schemas import ChecklistResponse

router = APIRouter(prefix="/api", tags=["체크리스트"])


@router.get("/checklist", response_model=ChecklistResponse, summary="경비 종류별 체크 항목")
def checklist(type: str = Query("국내출장", description="경비 종류")) -> dict:
    return service.get_checklist(type)
