"""규정 원문 보기 (U-03): 적재해 둔 규정을 조항 순서대로 그대로 보여 줍니다.

규정 Q&A 가 근거로 쓰는 것과 같은 자료(documents · chunks 테이블)라서, 답변의 근거 조항과 원문이 어긋나지 않습니다.
여기서는 읽기만 하고, 글을 고치거나 요약하지 않습니다.
직원에게는 직원 대상 규정만, 회계 관리자에게는 관리자용 규정까지 보입니다 (Q&A 와 같은 기준).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import AUDIENCE_ADMIN, AUDIENCE_ALL, AUDIENCE_EMPLOYEE, ROLE_ADMIN
from app.core.errors import AppError
from app.models import User
from app.models.knowledge import Chunk, Document


def _audiences(user: User) -> list[str]:
    if user.role == ROLE_ADMIN:
        return [AUDIENCE_ALL, AUDIENCE_EMPLOYEE, AUDIENCE_ADMIN]
    return [AUDIENCE_ALL, AUDIENCE_EMPLOYEE]


def _visible(user: User):
    return select(Document).where(Document.is_current.is_(True), Document.audience.in_(_audiences(user)))


def list_regulations(db: Session, user: User) -> list[dict]:
    """볼 수 있는 규정 목록 (이름순)."""
    counts = dict(db.execute(select(Chunk.document_id, func.count()).group_by(Chunk.document_id)).all())
    docs = db.scalars(_visible(user).order_by(Document.title)).all()
    return [
        {
            "id": d.id, "title": d.title, "doc_type": d.doc_type,
            "revised_at": d.revised_at.isoformat() if d.revised_at else None,
            "admin_only": d.audience == AUDIENCE_ADMIN,
            "sections": counts.get(d.id, 0),
        }
        for d in docs
    ]


def get_regulation(db: Session, user: User, doc_id: int) -> dict:
    """규정 한 건의 원문: 조항·별표·서식을 문서에 실린 순서대로."""
    doc = db.scalar(_visible(user).where(Document.id == doc_id))
    if doc is None:  # 없는 규정과 볼 수 없는 규정을 구분해 알려 주지 않음
        raise AppError("규정을 찾을 수 없습니다.", 404)
    chunks = db.scalars(select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.seq)).all()
    return {
        "id": doc.id, "title": doc.title, "doc_type": doc.doc_type,
        "revised_at": doc.revised_at.isoformat() if doc.revised_at else None,
        "source_url": doc.source_url,
        "sections": [
            {
                "seq": c.seq, "type": c.chunk_type, "article": c.article, "title": c.article_title,
                "chapter": (c.meta or {}).get("chapter") or None,
                "revised_at": c.revised_at.isoformat() if c.revised_at else None,
                "content": c.content,
            }
            for c in chunks
        ],
    }
