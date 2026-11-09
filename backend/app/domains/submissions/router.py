from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.domains.submissions import service
from app.domains.submissions.schemas import (
    DecisionRequest,
    RejectDraftRequest,
    RejectDraftResponse,
    SubmissionCreate,
    SubmissionList,
    SubmissionView,
)
from app.models import User

router = APIRouter(prefix="/api", tags=["정산 제출 · M-01 검토 대기함"])


# ---------- 직원 ----------
@router.post("/submissions", response_model=SubmissionView, status_code=201, summary="청구 내역 제출 (검토 요청)")
def create(req: SubmissionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.to_view(service.create_submission(db, user, req.model_dump()))


@router.get("/submissions", response_model=SubmissionList, summary="내 제출 내역")
def list_mine(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = service.list_submissions(db, user)
    return {"total": len(rows), "items": [service.to_view(s) for s in rows]}


# ---------- 회계 관리자 (M-01) ----------
@router.get("/admin/submissions", response_model=SubmissionList, summary="검토 대기함 목록 (전체)")
def list_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.require_admin(user)
    rows = service.list_submissions(db)
    return {"total": len(rows), "items": [service.to_view(s) for s in rows]}


@router.get("/admin/submissions/{code}", response_model=SubmissionView, summary="제출 건 상세")
def detail(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.require_admin(user)
    return service.to_view(service.get_submission(db, code))


@router.post("/admin/submissions/{code}/decision", response_model=SubmissionView, summary="승인 / 반려 저장")
def decide(code: str, req: DecisionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.require_admin(user)
    return service.to_view(service.decide(db, user, code, req.decision, req.message))


@router.post("/admin/submissions/{code}/reject-draft", response_model=RejectDraftResponse, summary="반려 메시지 초안 (근거 기반)")
def reject_draft(code: str, req: RejectDraftRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.require_admin(user)
    return service.reject_draft(db, code, req.issue_fields, req.extra_issues)
