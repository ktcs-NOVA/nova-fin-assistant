"""U-02 업무절차·필요서류 안내.

① 필요 서류 ② 작성 순서 ③ 제출 기한: tasks.py 에 조항과 함께 정해 둔 내용을 안내합니다.
④ 결재자: 위임전결규정 시행세칙 별표에서 조회합니다.
답하기 전에 근거 표현이 현재 규정에 있는지 확인하고, 없으면 옛 내용을 안내하지 않습니다.
안내 목록에 없는 업무도 지어내지 않고 "담당자 확인 필요"로 답합니다.
"""

import copy
import logging
import time
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.procedure.tasks import (
    APPROVAL_NOTE,
    DELEGATION,
    NO_APPROVAL_ROW,
    NO_APPROVAL_ROW_BASIS,
    TASKS,
    Cite,
    Item,
    ProcedureTask,
    match_task,
)
from app.models import Chunk, Document, QueryLog
from app.rag import retriever

log = logging.getLogger("nova.procedure")

NO_GROUND_SUMMARY = (
    "등록된 규정에서 이 업무의 절차를 찾지 못했습니다. 정확한 처리를 위해 담당자 확인이 필요합니다."
)

# 아직 규정을 적재하지 않았을 때 돌려주는 예시 (frontend/src/mocks/procedure.json 과 같은 모양)
SAMPLE = {
    "task": "국내 출장비 정산",
    "summary": (
        "(예시) 아직 규정 문서가 적재되지 않아 예시 답변을 보여줍니다. "
        "backend 폴더에서 'uv run python -m scripts.ingest' 를 실행하면 실제 규정으로 답합니다."
    ),
    "documents": [
        {"name": "출장원(정산)", "detail": "별지 제3호 서식", "basis": "여비규정 별지 제3호 서식"},
    ],
    "steps": [
        {
            "title": "출장보고서·출장원(정산) 작성",
            "detail": "출장 내용과 여비를 정확히 계산해 적습니다.",
            "basis": "여비규정 제3조의2 제3항",
        },
    ],
    "deadline": {"text": "출장을 마친 날부터 15일 이내", "basis": "여비규정 제3조의2 제2항"},
    "approver": {
        "text": "「위임전결규정 시행세칙」에서 정한 전결권자",
        "basis": "여비규정 제3조의2 제1항",
        "check": True,
    },
    "grounded": True,
    "sources": [{"ref": 1, "regulation": "여비규정", "article": "제3조의2"}],
}


@dataclass
class Article:
    regulation: str
    article: str
    content: str
    revised_at: date | None = None
    url: str | None = None


def no_ground_response(task: str) -> dict:
    return {
        "task": task,
        "summary": NO_GROUND_SUMMARY,
        "documents": [],
        "steps": [],
        "deadline": None,
        "approver": None,
        "grounded": False,
        "sources": [],
    }


def task_cites(task: ProcedureTask) -> list[Cite]:
    return [c for item in (*task.documents, *task.steps, task.deadline) for c in item.cites]


def missing_cites(task: ProcedureTask, articles: dict[tuple[str, str], Article]) -> list[Cite]:
    """현재 규정에서 근거 표현을 찾을 수 없는 항목. 띄어쓰기 차이는 무시합니다."""

    def squash(text: str) -> str:
        return "".join(text.split())

    missing = []
    for cite in task_cites(task):
        article = articles.get((cite.regulation, cite.article))
        if article is None or squash(cite.phrase) not in squash(article.content):
            missing.append(cite)
    return missing


def _basis(cites: tuple[Cite, ...]) -> str:
    """근거를 한 줄로. 같은 규정이면 규정명은 한 번만 씁니다."""
    labels: list[str] = []
    last_regulation = ""
    for cite in cites:
        label = (
            cite.label
            if cite.regulation != last_regulation
            else cite.label.removeprefix(f"{cite.regulation} ")
        )
        if label not in labels:
            labels.append(label)
        last_regulation = cite.regulation
    return ", ".join(labels)


def approver_text(contents: list[str], prefix: str, subject_suffix: str = "") -> str:
    """전결표 행 → '부서장을 제외한 직원: 부서장 / 부서장: 본부장'. 행이 없으면 빈 문자열."""
    pairs: dict[str, str] = {}
    notes: dict[str, None] = {}
    head = f"{prefix} > "
    for content in contents:
        for line in content.splitlines():
            if line.startswith(APPROVAL_NOTE):
                notes[line.strip()] = None
            if not line.startswith(head):
                continue
            rest = line[len(head) :]
            subject, _, approver = rest.partition(" → 전결권자: ")
            subject, _, remark = subject.partition(" (비고: ")
            approver, _, approver_remark = approver.partition(" (비고: ")
            who = approver or (remark or approver_remark).removesuffix(")")
            if who:
                pairs[subject.removesuffix(subject_suffix)] = who
    if not pairs:
        return ""
    rows = " / ".join(f"{subject}: {who}" for subject, who in pairs.items())
    return " ".join([rows, *notes])


def build_response(
    task: ProcedureTask,
    articles: dict[tuple[str, str], Article],
    approver: dict,
    approver_source: Article | None,
) -> dict:
    missing = missing_cites(task, articles)
    if missing:
        log.warning("%s: 규정에서 근거를 찾지 못함 %s", task.name, [c.label for c in missing])
        return no_ground_response(task.name)

    def documents(item: Item) -> dict:
        return {"name": item.name, "detail": item.detail, "basis": _basis(item.cites)}

    def steps(item: Item) -> dict:
        return {"title": item.name, "detail": item.detail, "basis": _basis(item.cites)}

    # 근거로 쓴 조항만, 처음 나온 순서대로 출처에 넣습니다
    used = dict.fromkeys((c.regulation, c.article) for c in task_cites(task))
    cited = [articles[key] for key in used]
    if approver_source is not None:
        cited.append(approver_source)
    sources = [
        {
            "ref": i,
            "regulation": a.regulation,
            "article": a.article,
            "revised_at": a.revised_at.isoformat() if a.revised_at else None,
            "url": a.url,
        }
        for i, a in enumerate(cited, start=1)
    ]
    return {
        "task": task.name,
        "summary": task.summary,
        "documents": [documents(x) for x in task.documents],
        "steps": [steps(x) for x in task.steps],
        "deadline": {
            "text": task.deadline.text,
            "basis": _basis(task.deadline.cites),
            "check": task.deadline.check,
        },
        "approver": approver,
        "grounded": True,
        "sources": sources,
    }


def _load_articles(db: Session, task: ProcedureTask) -> dict[tuple[str, str], Article]:
    """근거 조항을 읽습니다. 길어서 나뉜 조항은 조각을 다시 잇습니다."""
    articles = {}
    for key in dict.fromkeys((c.regulation, c.article) for c in task_cites(task)):
        rows = db.execute(
            select(Chunk, Document)
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.is_current.is_(True), Document.title == key[0], Chunk.article == key[1])
            .order_by(Chunk.seq)
        ).all()
        if rows:
            chunk, document = rows[0]
            content = "\n".join(c.content for c, _ in rows)
            # 서식처럼 개정 표시가 없는 조항은 문서의 최종 개정일을 씁니다
            revised = chunk.revised_at or document.revised_at
            articles[key] = Article(key[0], key[1], content, revised, document.source_url)
    return articles


def _load_approver(db: Session, task: ProcedureTask) -> tuple[dict, Article | None]:
    """④ 결재자: 시행세칙 별표에서 조회합니다. 항목이 없으면 확인 필요로 표시합니다."""
    if task.approval_prefix:
        rows = db.execute(
            select(Chunk, Document)
            .join(Document, Chunk.document_id == Document.id)
            .where(
                Document.is_current.is_(True),
                Document.title == DELEGATION,
                Chunk.chunk_type == "table",
                Chunk.content.contains(f"{task.approval_prefix} > "),
            )
        ).all()
        text = approver_text(
            [c.content for c, _ in rows], task.approval_prefix, task.subject_suffix
        )
        if text:
            chunk, document = rows[0]
            source = Article(DELEGATION, "별표", "", chunk.revised_at, document.source_url)
            return {"text": text, "basis": f"{DELEGATION} 별표", "check": False}, source

    document = db.scalar(
        select(Document).where(Document.title == DELEGATION, Document.is_current.is_(True))
    )
    source = None
    if document is not None:
        source = Article(DELEGATION, "제5조", "", document.revised_at, document.source_url)
    return {"text": NO_APPROVAL_ROW, "basis": NO_APPROVAL_ROW_BASIS, "check": True}, source


def get_procedure(db: Session, question: str) -> dict:
    if not retriever.has_documents(db):
        return copy.deepcopy(SAMPLE)

    started = time.perf_counter()
    task = match_task(question)
    if task is None:
        result = no_ground_response(question)
    else:
        result = _answer_task(db, task)

    _save_log(db, question, result, int((time.perf_counter() - started) * 1000))
    return result


def _answer_task(db: Session, task: ProcedureTask) -> dict:
    approver, approver_source = _load_approver(db, task)
    return build_response(task, _load_articles(db, task), approver, approver_source)


def get_procedure_by_name(db: Session, name: str) -> dict | None:
    """화면에 보여 준 업무 이름으로 절차를 다시 만듭니다 (체크리스트 저장용). 없는 업무면 None."""
    task = next((t for t in TASKS if t.name == name), None)
    return _answer_task(db, task) if task else None


def get_procedure_for_task(db: Session, name: str, question: str) -> dict | None:
    """챗봇이 절차 안내 도구를 고른 경우. 질문과 함께 질의 로그를 남깁니다."""
    started = time.perf_counter()
    result = get_procedure_by_name(db, name)
    if result is not None:
        _save_log(db, question, result, int((time.perf_counter() - started) * 1000))
    return result


def _save_log(db: Session, question: str, result: dict, latency_ms: int) -> None:
    """질의 로그 저장. 실패해도 답변은 나가도록 에러를 삼킴."""
    try:
        db.add(
            QueryLog(
                feature="procedure",
                question=question,
                answer=result["summary"],
                grounded=result["grounded"],
                sources=result["sources"],
                latency_ms=latency_ms,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        log.exception("질의 로그 저장 실패")
