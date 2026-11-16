"""문서 작업: 내 서류 저장·수정·초안 만들기. 다른 사람 서류는 없는 것처럼 404 로 답합니다.

정산 건에서 만든 서류는 그 건에 붙고(submission), 확인을 마치면 관리자에게 보낼 수 있습니다(sent_at).
지출결과서(+검수확인서)는 줄글 초안이 아니라 양식(forms.py)으로 만들어집니다.
"""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai import llm
from app.core.config import settings
from app.core.errors import AppError
from app.domains.documents import drafts, forms
from app.domains.submissions import service as submissions
from app.models import Submission, User, WorkDocument

KST = ZoneInfo("Asia/Seoul")

STATUS_WORKING = "작성 중"
STATUS_DONE = "작성 완료"

POLISH_SYSTEM = (
    "당신은 공공기관 보고서 문장 편집자입니다. 사용자가 적은 메모를 보고서 문체(~하였음, ~함)의 "
    "자연스러운 한 문단으로 다듬으세요. 메모에 없는 사실·날짜·금액·이름을 절대 추가하지 마세요. "
    "다듬은 문단만 출력하세요."
)
FILL_SYSTEM = (
    "당신은 공공기관 지출 증빙 서류 작성 보조입니다. 각 줄은 '키: 초안 문구' 입니다. "
    "초안을 서류에 적을 짧은 명사형 문구(30자 이내)로 다듬으세요. 초안에 없는 사실·날짜·금액·이름·인원을 "
    "절대 추가하지 마세요. 줄마다 '키: 문구' 형식 그대로, 받은 키만 출력하세요."
)


def _get(db: Session, user: User, doc_id: int) -> WorkDocument:
    doc = db.scalar(
        select(WorkDocument)
        .options(selectinload(WorkDocument.submission))
        .where(WorkDocument.id == doc_id, WorkDocument.user_id == user.id)
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
            .options(selectinload(WorkDocument.submission))
            .where(WorkDocument.user_id == user.id)
            .order_by(WorkDocument.updated_at.desc(), WorkDocument.id.desc())
        )
    )


def _my_submission(db: Session, user: User, code: str) -> Submission:
    """내가 낸 정산 건만. 남의 건은 없는 것처럼 404."""
    sub = submissions.get_submission(db, code)
    if sub.user_id != user.id:
        raise AppError(f"제출 건 {code} 을(를) 찾을 수 없습니다.", 404)
    return sub


def create_document(
    db: Session,
    user: User,
    kind: str,
    title: str | None,
    fields: dict,
    submission_code: str | None = None,
) -> WorkDocument:
    sub = _my_submission(db, user, submission_code) if submission_code else None

    if kind == forms.KIND:
        if sub is None:
            raise AppError("지출 결과서는 제출한 정산 건에서 만들 수 있습니다.")
        existing = db.scalar(
            select(WorkDocument)
            .options(selectinload(WorkDocument.submission))
            .where(
                WorkDocument.user_id == user.id,
                WorkDocument.kind == kind,
                WorkDocument.submission_id == sub.id,
            )
        )
        if existing is not None:
            return existing  # 한 정산 건에 결과서는 한 부
        view = submissions.to_view(sub)
        # 금액·날짜는 정산 건에서 읽으므로 저장하지 않고, AI 가 제안한 문구만 채워 둡니다.
        fields = {**forms.suggest(view), "ai_keys": forms.ai_keys(view)}
        title = (title or "").strip() or forms.default_title(view)

    doc = WorkDocument(
        user_id=user.id,
        submission_id=sub.id if sub else None,
        kind=kind,
        title=(title or "").strip() or drafts.default_title(kind, fields),
        fields=fields,
    )
    db.add(doc)
    db.commit()
    return _get(db, user, doc.id)


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
        if doc.kind == forms.KIND:
            lacking = _form(doc, user)["todo"]
            if lacking:
                names = ", ".join(t["label"] for t in lacking)
                raise AppError(f"아직 비어 있는 칸이 있습니다: {names}")
        elif not doc.draft.strip():
            raise AppError("초안이 아직 없어서 확인 완료로 바꿀 수 없습니다.")
        doc.confirmed = True
    elif req.confirmed is False or content_changed:
        doc.confirmed = False  # 내용이 바뀌면 다시 읽고 확인해야 함
    if content_changed or not doc.confirmed:
        doc.sent_at = None  # 보낸 뒤에 고치면 다시 보내야 함 (관리자가 옛 내용을 보지 않게)
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
    if doc.kind == forms.KIND:
        raise AppError("지출 결과서는 초안 대신 양식으로 만들어집니다.")
    lacking = drafts.missing(doc.kind, doc.fields)
    if lacking:
        raise AppError(f"초안을 만들려면 먼저 입력해 주세요: {', '.join(lacking)}")
    doc.draft = drafts.build(doc.kind, doc.fields, _who(user), polish=_polisher())
    doc.confirmed = False
    doc.sent_at = None
    doc.status = STATUS_WORKING
    db.commit()
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# 양식 (지출결과서 + 검수확인서) · 관리자에게 보내기
# ---------------------------------------------------------------------------
def _form(doc: WorkDocument, writer: User) -> dict:
    if doc.kind != forms.KIND:
        raise AppError("양식으로 보는 서류가 아닙니다.")
    if doc.submission is None:
        raise AppError("이 서류가 붙어 있던 정산 건이 없어졌습니다.", 404)
    today = (doc.sent_at or datetime.now(KST)).astimezone(KST).date()
    return forms.build(submissions.to_view(doc.submission), doc.fields, _who(writer), today)


def get_form(db: Session, user: User, doc_id: int) -> dict:
    return _form(_get(db, user, doc_id), user)


def fill_form(db: Session, user: User, doc_id: int) -> WorkDocument:
    """AI 칸(상세내역·용도)을 다시 채웁니다. 직원이 직접 고친 칸은 건드리지 않습니다."""
    doc = _get(db, user, doc_id)
    if doc.kind != forms.KIND or doc.submission is None:
        raise AppError("양식으로 보는 서류가 아닙니다.")
    base = forms.suggest(submissions.to_view(doc.submission))
    kept = set(doc.fields.get("ai_keys") or [])
    # 비어 있거나, 아직 AI 제안 그대로인 칸만 대상
    targets = {k: v for k, v in base.items() if not str(doc.fields.get(k) or "").strip() or k in kept}
    filled = _polish_cells(targets)
    doc.fields = {**doc.fields, **filled, "ai_keys": sorted(kept | set(filled))}
    doc.confirmed = False
    doc.sent_at = None
    doc.status = STATUS_WORKING
    db.commit()
    return _get(db, user, doc.id)


def _polish_cells(cells: dict[str, str]) -> dict[str, str]:
    """제안 문구를 AI 로 다듬습니다. AI 가 꺼져 있거나 실패하면 규칙으로 만든 문구를 그대로 씁니다."""
    if not cells or settings.ai_mock:
        return dict(cells)
    try:
        answer = llm.chat(FILL_SYSTEM, "\n".join(f"{k}: {v}" for k, v in cells.items()))
    except Exception:  # noqa: BLE001 — 다듬기는 선택 기능
        return dict(cells)
    out = dict(cells)
    for line in answer.splitlines():
        m = re.match(r"\s*([a-z]+_\d+)\s*[:：]\s*(.+)", line)
        if m and m.group(1) in cells and m.group(2).strip():
            out[m.group(1)] = m.group(2).strip()[:60]
    return out


def send_document(db: Session, user: User, doc_id: int) -> WorkDocument:
    """확인을 마친 서류를 정산 건의 증빙으로 관리자에게 보냅니다."""
    doc = _get(db, user, doc_id)
    if doc.submission is None:
        raise AppError("정산 건에서 만든 서류만 관리자에게 보낼 수 있습니다.")
    if not doc.confirmed:
        raise AppError("내용을 읽고 확인 표시를 한 뒤에 보낼 수 있습니다.")
    doc.sent_at = datetime.now(KST)
    db.commit()
    return _get(db, user, doc.id)


def submission_documents(db: Session, code: str) -> dict:
    """관리자: 이 정산 건에 붙어 온(보낸) 서류와, 아직 안 온 서류 종류."""
    sub = submissions.get_submission(db, code)
    docs = list(
        db.scalars(
            select(WorkDocument)
            .options(selectinload(WorkDocument.submission))
            .where(WorkDocument.submission_id == sub.id, WorkDocument.sent_at.is_not(None))
            .order_by(WorkDocument.sent_at, WorkDocument.id)
        )
    )
    expected = forms.expected_kinds(sub.type)
    got = {d.kind for d in docs}
    return {
        "expected": expected,
        "missing": [k for k in expected if k not in got],
        "documents": [
            {
                "id": d.id,
                "kind": d.kind,
                "title": d.title,
                "writer": _who(sub.user),
                "sent_at": d.sent_at,
                "draft": d.draft,
                "form": _form(d, sub.user) if d.kind == forms.KIND else None,
            }
            for d in docs
        ],
    }


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
