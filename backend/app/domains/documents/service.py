"""문서 작업: 내 서류 저장·수정·초안 만들기. 다른 사람 서류는 없는 것처럼 404 로 답합니다."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import llm
from app.core.config import settings
from app.core.errors import AppError
from app.domains.documents import drafts
from app.models import User, WorkDocument

STATUS_WORKING = "작성 중"
STATUS_DONE = "작성 완료"

POLISH_SYSTEM = (
    "당신은 공공기관 보고서 문장 편집자입니다. 사용자가 적은 메모를 보고서 문체(~하였음, ~함)의 "
    "자연스러운 한 문단으로 다듬으세요. 메모에 없는 사실·날짜·금액·이름을 절대 추가하지 마세요. "
    "다듬은 문단만 출력하세요."
)


def _get(db: Session, user: User, doc_id: int) -> WorkDocument:
    doc = db.scalar(
        select(WorkDocument).where(WorkDocument.id == doc_id, WorkDocument.user_id == user.id)
    )
    if doc is None:
        raise AppError("서류를 찾을 수 없습니다.", 404)
    return doc


def _who(user: User) -> str:
    return f"{user.name} ({user.department})"


def list_documents(db: Session, user: User) -> list[WorkDocument]:
    return list(
        db.scalars(
            select(WorkDocument)
            .where(WorkDocument.user_id == user.id)
            .order_by(WorkDocument.updated_at.desc(), WorkDocument.id.desc())
        )
    )


def create_document(
    db: Session, user: User, kind: str, title: str | None, fields: dict
) -> WorkDocument:
    doc = WorkDocument(
        user_id=user.id,
        kind=kind,
        title=(title or "").strip() or drafts.default_title(kind, fields),
        fields=fields,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document(db: Session, user: User, doc_id: int) -> WorkDocument:
    return _get(db, user, doc_id)


def update_document(db: Session, user: User, doc_id: int, req) -> WorkDocument:
    doc = _get(db, user, doc_id)
    content_changed = False
    if req.fields is not None and req.fields != doc.fields:
        doc.fields = req.fields
        content_changed = True
    if req.draft is not None and req.draft != doc.draft:
        doc.draft = req.draft
        content_changed = True
    if req.title is not None and req.title.strip():
        doc.title = req.title.strip()
    if req.confirmed is True:
        if not doc.draft.strip():
            raise AppError("초안이 아직 없어서 확인 완료로 바꿀 수 없습니다.")
        doc.confirmed = True
    elif req.confirmed is False or content_changed:
        doc.confirmed = False  # 내용이 바뀌면 다시 읽고 확인해야 함
    doc.status = STATUS_DONE if doc.confirmed else STATUS_WORKING
    db.commit()
    db.refresh(doc)
    return doc


def delete_document(db: Session, user: User, doc_id: int) -> None:
    db.delete(_get(db, user, doc_id))
    db.commit()


def make_draft(db: Session, user: User, doc_id: int) -> WorkDocument:
    """입력한 값으로 초안을 만들어 draft 에 저장. 비어 있는 칸이 있으면 400."""
    doc = _get(db, user, doc_id)
    lacking = drafts.missing(doc.kind, doc.fields)
    if lacking:
        raise AppError(f"초안을 만들려면 먼저 입력해 주세요: {', '.join(lacking)}")
    doc.draft = drafts.build(doc.kind, doc.fields, _who(user), polish=_polisher())
    doc.confirmed = False
    doc.status = STATUS_WORKING
    db.commit()
    db.refresh(doc)
    return doc


def _polisher():
    """실제 AI 가 켜져 있으면 메모를 다듬고, 꺼져 있거나 실패하면 메모 그대로 씁니다."""
    if settings.ai_mock:
        return lambda text: text

    def polish(text: str) -> str:
        try:
            return llm.chat(POLISH_SYSTEM, text).strip() or text
        except Exception:  # noqa: BLE001 — 다듬기는 선택 기능이라 실패해도 초안은 만든다
            return text

    return polish
