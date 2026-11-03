"""검색: 질문과 의미가 가까운 조각을 찾습니다 (pgvector 코사인 거리).

TODO
- 키워드 검색(Kiwi 형태소 + BM25) 섞기: "제14조", "자가용" 처럼 단어가 정확히 맞아야 하는 질문 대응
- 재정렬(reranker)로 상위 결과 다시 고르기
"""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import embed_query
from app.core.config import settings
from app.core.constants import AUDIENCE_ALL
from app.models import Chunk, Document

DEFAULT_TYPES = ("article", "table")  # 서식(form)은 기본 검색에서 제외


@dataclass
class Hit:
    chunk: Chunk
    document: Document
    score: float  # 코사인 유사도 (1에 가까울수록 비슷)


def has_documents(db: Session) -> bool:
    return (db.scalar(select(func.count()).select_from(Chunk)) or 0) > 0


def search(
    db: Session,
    query: str,
    *,
    k: int | None = None,
    audience: str | None = None,
    chunk_types: Sequence[str] = DEFAULT_TYPES,
) -> list[Hit]:
    k = k or settings.rag_top_k
    qv = embed_query(query)
    distance = Chunk.embedding.cosine_distance(qv).label("distance")

    stmt = (
        select(Chunk, Document, distance)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.is_current.is_(True), Chunk.embedding.is_not(None))
        .where(Chunk.chunk_type.in_(chunk_types))
    )
    if audience:  # 직원은 직원용+공통, 관리자는 관리자용+공통
        stmt = stmt.where(Document.audience.in_([AUDIENCE_ALL, audience]))
    stmt = stmt.order_by(distance).limit(k)

    return [Hit(chunk=c, document=d, score=1.0 - float(dist)) for c, d, dist in db.execute(stmt)]
