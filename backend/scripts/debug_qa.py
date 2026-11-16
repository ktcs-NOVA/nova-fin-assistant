"""질문이 왜 "근거 없음"으로 나오는지 확인합니다: 규정 적재 현황과 질문별 검색 상위 조각·점수를 보여 줍니다.

    uv run python -m scripts.debug_qa
    uv run python -m scripts.debug_qa "숙박비 상한은 얼마인가요?" "회의비에 참석자를 꼭 적어야 하나요?"

점수가 RAG_MIN_SCORE(.env, 기본 0.3) 보다 낮으면 답하지 않고 "담당자 확인 필요"가 됩니다.
"""

import sys

from sqlalchemy import func, select

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import Chunk, Document
from app.rag import retriever

DEFAULT_QUESTIONS = [
    "숙박비 상한은 얼마인가요?",
    "회의비에 참석자를 꼭 적어야 하나요?",
    "3급 직원 광역시 출장 숙박비 한도 얼마야?",
]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    questions = sys.argv[1:] or DEFAULT_QUESTIONS

    print(f"AI 모드: {'목업(API 키 없음)' if settings.ai_mock else '실제(OpenAI)'} · 점수 기준 RAG_MIN_SCORE={settings.rag_min_score}")
    with SessionLocal() as db:
        rows = db.execute(
            select(Document.title, Document.audience, Document.is_current, func.count(Chunk.id))
            .join(Chunk, Chunk.document_id == Document.id, isouter=True)
            .group_by(Document.id)
            .order_by(Document.title)
        ).all()
        print(f"\n적재된 문서 {len(rows)}건")
        for title, audience, current, n in rows:
            print(f"  - {title} [{audience}{'' if current else ', 지난 버전'}] 조각 {n}개")

        for q in questions:
            print(f"\n질문: {q}")
            hits = retriever.search(db, q, k=8, audience="employee")
            if not hits:
                print("  (검색 결과 없음: 직원용 문서가 적재되지 않았거나 임베딩이 비어 있어요)")
            for i, h in enumerate(hits, start=1):
                mark = "통과" if h.score >= settings.rag_min_score else "탈락"
                head = (h.chunk.content or "").replace("\n", " ")[:50]
                print(f"  {i}. [{mark}] {h.score:.3f}  {h.document.title} {h.chunk.article or ''}  ({h.chunk.chunk_type})  {head}")


if __name__ == "__main__":
    main()
