from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.domains.regulations import service
from app.models import User

router = APIRouter(prefix="/api/regulations", tags=["U-03 규정 원문 보기"])


class RegulationItem(BaseModel):
    id: int
    title: str
    doc_type: str
    revised_at: str | None = None
    admin_only: bool = False  # 회계 관리자에게만 보이는 규정
    sections: int  # 조항·별표·서식 수


class Section(BaseModel):
    seq: int
    type: str  # article(조문) / table(별표) / form(서식)
    article: str | None = None  # 제13조, 별표 1 …
    title: str | None = None  # 조 제목 (교통비)
    chapter: str | None = None  # 제2장 국내여비
    revised_at: str | None = None
    content: str  # 원문 그대로


class Regulation(BaseModel):
    id: int
    title: str
    doc_type: str
    revised_at: str | None = None
    source_url: str | None = None
    sections: list[Section]


@router.get("", response_model=list[RegulationItem], summary="볼 수 있는 규정 목록")
def list_regulations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.list_regulations(db, user)


@router.get("/{doc_id}", response_model=Regulation, summary="규정 한 건의 원문 (조항 순서대로)")
def get_regulation(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.get_regulation(db, user, doc_id)
