import logging
import time

from sqlalchemy.orm import Session

from app.domains.qa.schemas import QaResponse
from app.models import QueryLog
from app.rag import answerer, retriever

log = logging.getLogger("nova.qa")

# 아직 규정을 적재하지 않았을 때 돌려주는 예시 (frontend/src/mocks/qa.json 과 같은 모양)
SAMPLE = {
    "answer": (
        "(예시) 아직 규정 문서가 적재되지 않아 예시 답변을 보여줍니다. "
        "backend 폴더에서 'uv run python -m scripts.ingest' 를 실행하면 실제 규정으로 답합니다."
    ),
    "sources": [
        {"regulation": "여비규정", "article": "제13조 제5항"},
        {"regulation": "여비규정", "article": "제13조 제6항"},
    ],
}


def answer_question(db: Session, question: str) -> QaResponse:
    if not retriever.has_documents(db):
        return QaResponse.model_validate(SAMPLE)

    started = time.perf_counter()
    result = answerer.answer(db, question)
    latency_ms = int((time.perf_counter() - started) * 1000)

    _save_log(db, question, result, latency_ms)
    return QaResponse(answer=result.answer, grounded=result.grounded, sources=result.sources)


def _save_log(db: Session, question: str, result: answerer.RagAnswer, latency_ms: int) -> None:
    """질의 로그 저장. 실패해도 답변은 나가도록 에러를 삼킴."""
    try:
        db.add(
            QueryLog(
                feature="qa",
                question=question,
                answer=result.answer,
                grounded=result.grounded,
                sources=result.sources,
                retrieved=[
                    {"chunk_id": h.chunk.id, "score": round(h.score, 4)} for h in result.hits
                ],
                latency_ms=latency_ms,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        log.exception("질의 로그 저장 실패")
