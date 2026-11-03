"""문서 적재: 파일 → 텍스트 → 조 단위 조각 → 임베딩 → DB(documents, chunks).

같은 규정명의 문서가 이미 있으면:
  - 파일 내용이 같으면 건너뜀 (임베딩 비용 절약)
  - 바뀌었으면 기존 문서를 지우고 새로 적재
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import embed_texts
from app.core.constants import AUDIENCE_ALL
from app.models import Chunk, Document
from app.rag.chunker import document_revised_at, split_regulation
from app.rag.loader import load_text


@dataclass
class IngestResult:
    title: str
    status: str  # created / updated / skipped
    chunks: int = 0


def title_from_filename(path: Path) -> str:
    """'여비규정(2026.10.21).hwp' → '여비규정'"""
    return re.sub(r"\s*\([^)]*\)\s*$", "", path.stem).strip()


def ingest_file(
    db: Session,
    path: str | Path,
    *,
    title: str | None = None,
    audience: str = AUDIENCE_ALL,
    doc_type: str = "규정",
    source_url: str | None = None,
    force: bool = False,
) -> IngestResult:
    path = Path(path)
    title = title or title_from_filename(path)
    content_hash = hashlib.sha256(path.read_bytes()).hexdigest()

    existing = db.scalars(select(Document).where(Document.title == title)).all()
    if not force and any(d.content_hash == content_hash for d in existing):
        return IngestResult(title, "skipped")

    text = load_text(path)
    drafts = split_regulation(text)
    if not drafts:
        raise ValueError(f"{path.name}: 조문을 찾지 못했습니다. 문서 형식을 확인해 주세요.")

    vectors = embed_texts([d.embed_text(title) for d in drafts])

    for old in existing:
        db.delete(old)  # 조각은 cascade 로 같이 삭제

    doc = Document(
        title=title,
        doc_type=doc_type,
        audience=audience,
        source_file=path.name,
        source_url=source_url,
        revised_at=document_revised_at(text),
        is_current=True,
        content_hash=content_hash,
    )
    doc.chunks = [
        Chunk(
            seq=d.seq,
            chunk_type=d.chunk_type,
            article=d.article,
            article_title=d.article_title,
            content=d.content,
            revised_at=d.revised_at,
            meta=d.meta,
            embedding=vec,
        )
        for d, vec in zip(drafts, vectors, strict=True)
    ]
    db.add(doc)
    db.commit()
    return IngestResult(title, "updated" if existing else "created", len(drafts))
