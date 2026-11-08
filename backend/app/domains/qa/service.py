import logging
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import CONTACT_EMPLOYEE_NO
from app.domains.procedure import service as procedure_service
from app.domains.qa import assistant
from app.domains.qa.schemas import ContactInfo, QaResponse
from app.models import QueryLog, User
from app.rag import answerer, retriever

log = logging.getLogger("nova.qa")

CLARIFY_ANSWER = "어떤 업무의 절차를 안내할까요? 아래에서 골라 주세요."
# 되묻기 버튼 순서 (자주 쓰는 업무 먼저)
CLARIFY_OPTIONS = [
    "국내 출장비 정산",
    "국외 출장비 정산",
    "법인카드 사용 후 처리",
    "업무추진비 집행",
]


def ask(db: Session, question: str) -> QaResponse:
    """챗봇 입구. 질문에 맞는 도구를 골라 규정 답변, 절차 안내, 되묻기 중 하나로 답합니다."""
    if not retriever.has_documents(db):
        return QaResponse.model_validate(SAMPLE)

    picked = assistant.route(question)
    log.info("도구 선택: %s %s (%s)", picked.kind, picked.task or "", picked.by)

    if picked.kind == "clarify":
        return QaResponse(
            type="clarify", answer=CLARIFY_ANSWER, sources=[], options=CLARIFY_OPTIONS
        )
    if picked.kind == "procedure":
        procedure = procedure_service.get_procedure_for_task(db, picked.task, question)
        # 규정이 개정되어 절차를 안내할 수 없으면 일반 답변으로 넘어갑니다
        if procedure is not None and procedure["grounded"]:
            return QaResponse(
                type="procedure",
                answer=procedure["summary"],
                sources=procedure["sources"],
                procedure=procedure,
            )
    return answer_question(db, question)


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
    return QaResponse(
        answer=result.answer,
        grounded=result.grounded,
        sources=result.sources,
        contact=None if result.grounded else _contact(db),
    )


def _contact(db: Session) -> ContactInfo | None:
    """근거를 못 찾았을 때 안내할 담당자. 계정이 없으면 None."""
    user = db.scalar(select(User).where(User.employee_no == CONTACT_EMPLOYEE_NO))
    if user is None:
        return None
    return ContactInfo(department=user.department, name=user.name, phone=user.phone or "")


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
