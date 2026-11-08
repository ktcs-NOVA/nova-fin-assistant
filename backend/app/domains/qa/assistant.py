"""질문을 보고 어떤 방식으로 답할지 고릅니다 (챗봇의 도구 선택).

    answer_question  규정 내용(금액, 한도, 가능 여부)을 묻는 질문 → RAG 답변 (U-01)
    guide_procedure  해야 할 일, 준비물, 처리 순서를 묻는 질문 → 절차 안내 (U-02)
    ask_which_task   절차를 묻지만 어떤 업무인지 모를 때 → 되묻기

LLM 은 도구와 업무 이름만 고릅니다. 절차 내용은 procedure 규칙 엔진이 만들므로 LLM 이 지어낼 수 없습니다.
API 키가 없거나 호출이 실패하면 단어 규칙(match_task)으로 고릅니다.
"""

import logging
from dataclasses import dataclass
from typing import Literal

from app.ai import choose_tool
from app.domains.procedure.tasks import TASKS, match_task

log = logging.getLogger("nova.assistant")

TASK_NAMES = [t.name for t in TASKS]

Kind = Literal["answer", "procedure", "clarify"]

SYSTEM_PROMPT = """당신은 한국해양진흥공사 경비 규정 도우미의 안내 담당입니다.
직원의 질문을 보고 도구를 정확히 하나 고릅니다.

- 해야 할 일, 준비할 서류, 처리 순서, 다음 단계처럼 "무엇을 어떻게 진행하는지"를 물으면 guide_procedure
- 금액, 한도, 기한 하나, 가능 여부, 조건처럼 "규정 내용 하나"를 물으면 answer_question
- 진행 방법을 묻지만 어떤 업무인지 알 수 없으면 ask_which_task
- guide_procedure 의 업무 목록에 없는 업무(연차, 휴가, 법인카드 분실 등)는 answer_question

업무 고르는 법:
- 출장, 출장비, 여비가 나오면 출장비 정산입니다. 해외·국외라는 말이 없으면 국내 출장비 정산입니다.
- 법인카드, 법카, 회사카드를 쓴 뒤의 일(지출결의, 전표, 영수증)은 법인카드 사용 후 처리입니다.
- 업무추진비, 조직관리비, 거래처 접대는 업무추진비 집행입니다.
- 질문에 업무가 드러나 있으면 ask_which_task 를 쓰지 않습니다. 업무 단서가 전혀 없을 때만 되묻습니다.
- 위 업무의 결재자·전결권자·승인권자를 물으면 guide_procedure 입니다 (결재자는 절차 안내에 들어 있습니다)."""

# LLM 이 되묻기를 골라도 질문에 업무 단서가 있으면 그 업무로 안내합니다.
# (국내·국외가 안 적힌 출장 질문을 LLM 이 자꾸 되묻는 문제 — 국외라는 말이 없으면 국내로 봅니다)
_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("해외", "국외", "외국"), "국외 출장비 정산"),
    (("업무추진비", "조직관리비", "접대"), "업무추진비 집행"),
    (("출장", "여비"), "국내 출장비 정산"),
    (("법인카드", "법카", "회사카드"), "법인카드 사용 후 처리"),
)


def task_hint(question: str) -> str | None:
    text = "".join(question.split())
    return next((task for words, task in _HINTS if any(w in text for w in words)), None)


TOOLS = [
    {
        "name": "guide_procedure",
        "description": "업무를 처리하는 절차(필요 서류, 작성 순서, 제출 기한, 결재자)를 단계별로 안내합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "enum": TASK_NAMES, "description": "안내할 업무"}
            },
            "required": ["task"],
        },
    },
    {
        "name": "answer_question",
        "description": "규정 조항을 찾아 질문에 답합니다.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "ask_which_task",
        "description": "절차를 묻지만 어떤 업무인지 알 수 없을 때 업무를 되묻습니다.",
        "parameters": {"type": "object", "properties": {}},
    },
]


@dataclass(frozen=True)
class Route:
    kind: Kind
    task: str | None = None  # kind 가 procedure 일 때 업무 이름
    by: str = "llm"  # llm / rule (어떻게 골랐는지, 로그·평가용)


def rule_route(question: str) -> Route:
    task = match_task(question)
    return Route("procedure", task.name, by="rule") if task else Route("answer", by="rule")


def route(question: str) -> Route:
    try:
        picked = choose_tool(SYSTEM_PROMPT, question, TOOLS)
    except Exception:
        log.exception("도구 선택 실패, 단어 규칙으로 대신함")
        picked = None
    if picked is None:
        return rule_route(question)

    name, args = picked
    if name == "guide_procedure" and args.get("task") in TASK_NAMES:
        return Route("procedure", args["task"])
    if name == "ask_which_task":
        hint = task_hint(question)
        return Route("procedure", hint, by="llm+hint") if hint else Route("clarify")
    if name == "answer_question":
        return Route("answer")
    log.warning("알 수 없는 도구 선택 %s %s, 단어 규칙으로 대신함", name, args)
    return rule_route(question)
