"""답변: 검색된 조항만 근거로 답하고, 출처를 붙입니다 (U-01 · U-03).

근거 원칙 (U-03)
- 검색 점수가 RAG_MIN_SCORE 보다 낮으면 답하지 않고 "담당자 확인 필요" 로 안내
- 답변 안의 [번호] 인용을 보고 실제로 쓴 조항만 출처로 돌려줌
"""

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.ai import chat
from app.core.config import settings
from app.core.constants import AUDIENCE_EMPLOYEE
from app.rag.retriever import Hit, search

NO_GROUND_ANSWER = (
    "등록된 규정에서 이 질문의 근거 조항을 찾지 못했습니다. "
    "정확한 처리를 위해 담당자 확인이 필요합니다."
)

SYSTEM_PROMPT = """당신은 한국해양진흥공사 임직원의 경비·회계 규정 질문에 답하는 도우미입니다.
규칙:
1. 아래 [참고 조항]에 있는 내용만 근거로 답합니다. 조항에 없는 내용은 추측하지 않습니다.
2. 근거로 쓴 조항은 문장 끝에 [1], [2] 처럼 번호로 표시합니다.
3. 조항만으로 판단할 수 없으면 "담당자 확인이 필요합니다"라고 분명히 말합니다.
4. 금액·기한·필요 서류처럼 실무에 필요한 내용을 먼저, 짧고 쉬운 문장으로 답합니다."""


@dataclass
class RagAnswer:
    answer: str
    sources: list[dict]
    grounded: bool
    hits: list[Hit] = field(default_factory=list)


def _label(hit: Hit) -> str:
    c = hit.chunk
    title = f"({c.article_title})" if c.article_title else ""
    revised = f" · 개정 {c.revised_at.isoformat()}" if c.revised_at else ""
    return f"{hit.document.title} {c.article or ''}{title}{revised}"


def _source(hit: Hit) -> dict:
    return {
        "regulation": hit.document.title,
        "article": hit.chunk.article or "",
        "revised_at": hit.chunk.revised_at.isoformat() if hit.chunk.revised_at else None,
        "url": hit.document.source_url,
    }


def answer(db: Session, question: str, *, audience: str = AUDIENCE_EMPLOYEE) -> RagAnswer:
    hits = search(db, question, audience=audience)

    if settings.ai_mock:
        # 목업 임베딩은 의미 검색이 안 되므로 점수 기준을 적용하지 않고 흐름만 보여줌
        grounded_hits = hits[:3]
    else:
        grounded_hits = [h for h in hits if h.score >= settings.rag_min_score]

    if not grounded_hits:
        return RagAnswer(NO_GROUND_ANSWER, [], grounded=False, hits=hits)

    context = "\n\n".join(
        f"[{i}] {_label(h)}\n{h.chunk.content}" for i, h in enumerate(grounded_hits, start=1)
    )
    reply = chat(SYSTEM_PROMPT, f"질문: {question}\n\n[참고 조항]\n{context}")

    if settings.ai_mock:
        reply += "\n\n(검색된 조항: " + ", ".join(_label(h) for h in grounded_hits) + ")"

    # 답변에서 실제로 인용한 번호만 출처로. 인용이 없으면 검색된 조항 전체.
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", reply)}
    used = [h for i, h in enumerate(grounded_hits, start=1) if i in cited] or grounded_hits

    sources, seen = [], set()
    for h in used:
        key = (h.document.title, h.chunk.article)
        if key not in seen:
            seen.add(key)
            sources.append(_source(h))

    return RagAnswer(reply, sources, grounded=True, hits=hits)
