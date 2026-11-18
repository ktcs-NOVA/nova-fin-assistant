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
1. 아래 [참고 조항]에 있는 내용만 근거로 답합니다. 금액·한도·기한·서식 번호는 조항에 적힌 것만 쓰고, 조항에 없는 숫자는 절대 만들지 않습니다.
2. 질문의 핵심(예: 1인당 한도, 남은 예산, 반려 여부)이 조항에 직접 나오지 않으면 결론을 짐작하지 말고, 관련 조항만 짧게 소개한 뒤 "담당자 확인이 필요합니다"라고 분명히 말합니다.
3. 근거로 쓴 조항은 문장 끝에 [1], [2] 처럼 번호로 표시합니다.
4. 조항으로 답할 수 있으면 결론을 먼저, 짧고 쉬운 문장으로 말합니다. 금액·기한·필요 서류처럼 실무에 필요한 내용을 함께 적습니다.
5. 조항에 "다만", "단", "불가피한 경우" 같은 예외가 있으면 그 조건과 그때 필요한 서식(별지 제○호)·승인을 함께 안내합니다.
6. 해당 항목은 규정 용어 그대로 씁니다. (예: 노래방은 "레저업종"이라 클린카드 사용 제한, 나눠 결제한 2건 이상은 "1건으로 보아" 적용)
7. 표(별표)는 질문의 직급·지역·구분에 맞는 행과 열을 찾아 숫자를 그대로 씁니다. 단위가 천원이면 원으로도 적습니다. (예: 90천원 = 90,000원)
8. 전결표에서 결재자를 찾을 때는 "직원복무" 항목처럼 직원 본인의 결재 행을 고르고, 대상이 나뉘면(예: 부서장 / 부서장을 제외한 직원) 질문한 사람에 맞는 행을 씁니다. 특정 부서의 관리 업무 행(예: 인사팀 > 출장 및 여비관리)은 직원 본인의 결재가 아닙니다.
9. 조항이 다른 규정을 따르라고 하면(예: 「법인카드 관리 및 사용 지침」에 따른다) 그 규정의 조항이 [참고 조항]에 있을 때 이어서 답합니다.
10. "이 질문은 ~에 해당합니다" 같은 맺음말은 붙이지 않습니다."""


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

    reply, sources, grounded = tidy_citations(reply, grounded_hits)
    return RagAnswer(reply, sources, grounded=grounded, hits=hits)


def tidy_citations(reply: str, hits: list[Hit]) -> tuple[str, list[dict], bool]:
    """답변의 [n] 인용을 출처 목록과 맞춥니다 (U-03). 반환: (정리된 답변, 출처, 근거 여부)

    - 실제로 인용한 조항만 출처로, 번호는 등장 순서대로 1, 2, 3… 으로 다시 매김
    - 검색 결과에 없는 번호(지어낸 인용)는 본문에서 지움
    - 인용 없이 "담당자 확인"으로 답했으면 근거 없음 (출처를 붙이지 않음)
    - 인용 표시 없이 답했으면 검색된 조항 전체를 근거로
    """
    cited = [int(n) for n in re.findall(r"\[(\d+)\]", reply)]
    if not cited and "담당자 확인" in reply:
        return reply, [], False

    order = list(dict.fromkeys(n for n in cited if 1 <= n <= len(hits)))
    if not order:
        order = list(range(1, len(hits) + 1))

    renumber, sources, seen = {}, [], {}
    for old in order:
        h = hits[old - 1]
        key = (h.document.title, h.chunk.article)
        if key in seen:  # 같은 조항의 다른 조각이면 같은 번호로
            renumber[old] = seen[key]
            continue
        new = len(sources) + 1
        seen[key] = renumber[old] = new
        sources.append({"ref": new, **_source(h)})

    def _swap(m: re.Match) -> str:
        n = int(m[1])
        return f"[{renumber[n]}]" if n in renumber else ""

    return re.sub(r"\[(\d+)\]", _swap, reply), sources, True
