from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.domains.documents import service as documents
from app.domains.submissions import service
from app.domains.submissions.schemas import (
    DecisionRequest,
    RejectDraftRequest,
    RejectDraftResponse,
    SubmissionCreate,
    SubmissionList,
    SubmissionView,
)
from app.models import Submission, User

router = APIRouter(prefix="/api", tags=["정산 제출 · M-01 검토 대기함"])


def _views(db: Session, subs: list) -> list[dict]:
    """제출 건 응답 + 증빙 서류 상태(docs: 받아야 할 것 · 받은 것 · 안 온 것)."""
    status = documents.doc_status(db, subs)
    # 반려된 건을 고쳐 다시 낸 건이 있으면 그 새 번호 (가장 최근 것)
    codes = [s.code for s in subs]
    again: dict[str, str] = {}
    if codes:
        rows = db.execute(
            select(Submission.resubmit_of, Submission.code).where(Submission.resubmit_of.in_(codes)).order_by(Submission.id)
        )
        again = {old: new for old, new in rows}
    return [{**service.to_view(s), "docs": status[s.id], "resubmitted_as": again.get(s.code)} for s in subs]


# ---------- 직원 ----------
@router.post("/submissions", response_model=SubmissionView, status_code=201, summary="청구 내역 제출 (검토 요청)")
def create(req: SubmissionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.to_view(service.create_submission(db, user, req.model_dump()))


@router.get("/submissions", response_model=SubmissionList, summary="내 제출 내역")
def list_mine(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = service.list_submissions(db, user)
    return {"total": len(rows), "items": _views(db, rows)}


# ---------- 회계 관리자 (M-01) ----------
@router.get("/admin/submissions", response_model=SubmissionList, summary="검토 대기함 목록 (전체)")
def list_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.require_admin(user)
    rows = service.list_submissions(db)
    return {"total": len(rows), "items": _views(db, rows)}


@router.get("/admin/submissions/{code}", response_model=SubmissionView, summary="제출 건 상세")
def detail(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.require_admin(user)
    return _views(db, [service.get_submission(db, code)])[0]


@router.post("/admin/submissions/{code}/decision", response_model=SubmissionView, summary="승인 / 반려 저장")
def decide(code: str, req: DecisionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.require_admin(user)
    return service.to_view(service.decide(db, user, code, req.decision, req.message, req.issues))


@router.post("/admin/submissions/{code}/reject-draft", response_model=RejectDraftResponse, summary="반려 메시지 초안 (근거 기반)")
def reject_draft(code: str, req: RejectDraftRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    service.require_admin(user)
    return service.reject_draft(db, code, req.issue_fields, req.extra_issues)
