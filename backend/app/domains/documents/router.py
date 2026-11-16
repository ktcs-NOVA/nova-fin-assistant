from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.domains.documents import service
from app.domains.documents.schemas import (
    DocumentCreate,
    DocumentOut,
    DocumentUpdate,
    SubmissionDocuments,
)
from app.domains.submissions.service import require_admin
from app.models import User

router = APIRouter(prefix="/api/documents", tags=["문서 작업"])


@router.get(
    "", response_model=list[DocumentOut], summary="내 작성 중·완료 서류 목록 (최근 수정 순)"
)
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.list_documents(db, user)


@router.post("", response_model=DocumentOut, status_code=201, summary="새 서류 만들기")
def create_document(
    req: DocumentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return service.create_document(
        db, user, req.kind, req.title, req.fields, req.submission_code
    )


@router.get("/{doc_id}", response_model=DocumentOut, summary="서류 한 건")
def get_document(
    doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return service.get_document(db, user, doc_id)


@router.patch("/{doc_id}", response_model=DocumentOut, summary="입력값·초안·확인 여부 저장")
def update_document(
    doc_id: int,
    req: DocumentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.update_document(db, user, doc_id, req)


@router.delete("/{doc_id}", status_code=204, summary="서류 삭제")
def delete_document(
    doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    service.delete_document(db, user, doc_id)
    return Response(status_code=204)


@router.post("/{doc_id}/draft", response_model=DocumentOut, summary="입력한 값으로 초안 만들기")
def make_draft(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.make_draft(db, user, doc_id)


@router.get("/{doc_id}/form", summary="양식 (지출결과서 · 회의록 · 출장보고서, 칸마다 출처 표시)")
def get_form(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.get_form(db, user, doc_id)


@router.post("/{doc_id}/fill", response_model=DocumentOut, summary="AI 가 쓰는 칸 채우기 (문구 제안 · 메모 다듬기)")
def fill_form(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.fill_form(db, user, doc_id)


@router.post("/{doc_id}/send", response_model=DocumentOut, summary="확인한 서류를 관리자에게 보내기")
def send_document(
    doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return service.send_document(db, user, doc_id)


# 관리자: 정산 건에 붙어 온 서류 (M-01 상세의 "첨부 서류" 카드)
admin_router = APIRouter(prefix="/api/admin/submissions", tags=["문서 작업"])


@admin_router.get(
    "/{code}/documents", response_model=SubmissionDocuments, summary="정산 건에 붙어 온 서류"
)
def submission_documents(
    code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    require_admin(user)
    return service.submission_documents(db, code)
