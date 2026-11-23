"""U-03 규정 원문 보기: 검색용으로 잘게 나눠 둔 조각(chunks)을 다시 이어 붙여 원문 순서대로 돌려줍니다.

조각을 나눈 방식 (app/rag/chunker.py)
- 긴 조문은 항 단위로 나뉘고, 뒤 조각 첫 줄이 '제14조(…) (계속)'
- 긴 별표는 행 단위로 나뉘고, 뒤 조각 첫 줄이 '[별표 1] … (계속)'
- 전결표(<별표>)는 구역·업무별로 나뉘고, 조각마다 첫 줄 '<별표> 1. 전사 공통 사항 · 가. 일반'과
  끝의 '※ 안내'가 반복됨
→ 같은 조항(전결표는 같은 구역)끼리 모아 이어 붙이고, 반복된 머리 줄·안내는 한 번만 남깁니다.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import AUDIENCE_ALL, AUDIENCE_EMPLOYEE
from app.models import Chunk, Document

_CONTINUED = "(계속)"
_APPROVAL_HEAD = "<별표>"


@dataclass
class _Section:
    article: str
    title: str | None
    kind: str
    chapter: str | None
    head: str | None
    revised_at: str | None
    lines: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # 전결표의 ※ 안내 (조각마다 반복 → 끝에 한 번만)

    def add(self, content: str) -> None:
        lines = content.splitlines()
        if (
            lines
            and self.lines
            and (lines[0].rstrip().endswith(_CONTINUED) or lines[0] == self.head)
        ):
            lines = lines[1:]  # 이어지는 조각의 머리 줄은 이미 있음
        for ln in lines:
            if self.head and ln.lstrip().startswith(("※", "* ")):
                if ln not in self.notes:
                    self.notes.append(ln)
            elif not (self.head and ln in self.lines):
                self.lines.append(ln)

    @property
    def content(self) -> str:
        return "\n".join(self.lines + self.notes).strip()


def _iso(d) -> str | None:
    return d.isoformat() if d else None


def build_sections(chunks: Iterable) -> list[dict]:
    """seq 순서의 조각들을 조항(전결표는 구역) 단위로 묶어 원문 순서대로 돌려줍니다."""
    sections: dict[tuple, _Section] = {}
    approval_count = 0
    for c in chunks:
        article = c.article or ""
        first = c.content.splitlines()[0] if c.content else ""
        head = first if first.startswith(_APPROVAL_HEAD) else None
        key = (c.chunk_type, article, head)
        if key not in sections:
            sections[key] = _Section(
                article=article,
                title=c.article_title,
                kind=c.chunk_type,
                chapter=(c.meta or {}).get("chapter") or None,
                head=head,
                revised_at=_iso(c.revised_at),
            )
            if head:
                approval_count += 1
        sections[key].add(c.content)

    out, used = [], set()
    for (kind, article, head), s in sections.items():
        key = article or kind
        if head or key in used:  # 같은 이름이 여러 개면 번호를 붙여 구분 (전결표 구역 등)
            n = 1
            while f"{key}#{n}" in used:
                n += 1
            key = f"{key}#{n}"
        used.add(key)
        out.append(
            {
                "key": key,
                "article": s.article,
                "title": s.title,
                "kind": s.kind,
                "chapter": s.chapter,
                "head": head.removeprefix(_APPROVAL_HEAD).strip() if head else None,
                "revised_at": s.revised_at,
                "content": s.content,
            }
        )
    return out


def _audiences(role: str | None) -> Sequence[str]:
    """직원은 공통+직원용, 관리자는 공통+관리자용 문서만 (검색과 같은 기준)."""
    return [AUDIENCE_ALL, role or AUDIENCE_EMPLOYEE]


def _visible(stmt, role: str | None):
    return stmt.where(Document.is_current.is_(True), Document.audience.in_(_audiences(role)))


def list_regulations(db: Session, role: str | None) -> list[dict]:
    """원문으로 볼 수 있는 규정 목록 (제목 순)."""
    counts = (
        select(Chunk.document_id, func.count(func.distinct(Chunk.article)).label("n"))
        .group_by(Chunk.document_id)
        .subquery()
    )
    stmt = _visible(
        select(Document, counts.c.n).join(counts, counts.c.document_id == Document.id), role
    ).order_by(Document.title)
    return [
        {"id": d.id, "title": d.title, "revised_at": _iso(d.revised_at), "sections": n}
        for d, n in db.execute(stmt)
    ]


def get_regulation(db: Session, doc_id: int, role: str | None) -> dict | None:
    doc = db.scalar(_visible(select(Document).where(Document.id == doc_id), role))
    if doc is None:
        return None
    chunks = db.scalars(select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.seq))
    return {
        "id": doc.id,
        "title": doc.title,
        "revised_at": _iso(doc.revised_at),
        "source_file": doc.source_file,
        "sections": build_sections(chunks),
    }
