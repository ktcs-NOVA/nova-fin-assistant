"""챗봇 도구 선택과 통합 응답 테스트 — DB·API 키 없이 실행."""

import pytest

from app.domains.qa import assistant, service
from app.domains.qa.assistant import Route


def _pick(monkeypatch, result):
    def fake(system, user, tools):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(assistant, "choose_tool", fake)


def test_tools_offer_only_known_tasks():
    guide = next(t for t in assistant.TOOLS if t["name"] == "guide_procedure")
    assert guide["parameters"]["properties"]["task"]["enum"] == assistant.TASK_NAMES


@pytest.mark.parametrize(
    ("picked", "expected"),
    [
        (("guide_procedure", {"task": "국내 출장비 정산"}), Route("procedure", "국내 출장비 정산")),
        (("ask_which_task", {}), Route("clarify")),
        (("answer_question", {}), Route("answer")),
    ],
)
def test_route_follows_llm_choice(monkeypatch, picked, expected):
    _pick(monkeypatch, picked)
    assert assistant.route("아무 질문") == expected


@pytest.mark.parametrize(
    "picked",
    [
        None,  # 목업 모드
        ("guide_procedure", {"task": "지어낸 업무"}),
        ("unknown_tool", {}),
        RuntimeError("API 오류"),
    ],
)
def test_route_falls_back_to_word_rules(monkeypatch, picked):
    _pick(monkeypatch, picked)
    assert assistant.route("법인카드 쓰고 나서 처리할 일은?") == Route(
        "procedure", "법인카드 사용 후 처리", by="rule"
    )
    assert assistant.route("숙박비 한도 얼마야?") == Route("answer", by="rule")


@pytest.fixture
def ready(monkeypatch):
    monkeypatch.setattr(service.retriever, "has_documents", lambda db: True)
    answered = []

    def fake_answer(db, question):
        answered.append(question)
        return service.QaResponse(answer="규정 답변", sources=[])

    monkeypatch.setattr(service, "answer_question", fake_answer)
    return answered


PROCEDURE = {
    "task": "국내 출장비 정산",
    "summary": "15일 이내에 정산합니다.",
    "documents": [{"name": "출장보고서", "detail": "", "basis": "여비규정 별지 제4호 서식"}],
    "steps": [],
    "deadline": None,
    "approver": None,
    "grounded": True,
    "sources": [{"ref": 1, "regulation": "여비규정", "article": "별지 제4호 서식"}],
}


def test_procedure_route_returns_procedure_card(monkeypatch, ready):
    monkeypatch.setattr(assistant, "route", lambda q: Route("procedure", "국내 출장비 정산"))
    monkeypatch.setattr(
        service.procedure_service, "get_procedure_for_task", lambda db, name, q: PROCEDURE
    )
    res = service.ask(None, "출장 다녀오면 뭐 해?")
    assert res.type == "procedure"
    assert res.answer == PROCEDURE["summary"]
    assert res.procedure.documents[0].name == "출장보고서"
    assert res.sources[0].article == "별지 제4호 서식"
    assert ready == []


def test_procedure_without_grounds_falls_back_to_answer(monkeypatch, ready):
    monkeypatch.setattr(assistant, "route", lambda q: Route("procedure", "국내 출장비 정산"))
    monkeypatch.setattr(
        service.procedure_service,
        "get_procedure_for_task",
        lambda db, name, q: {**PROCEDURE, "grounded": False},
    )
    res = service.ask(None, "출장 다녀오면 뭐 해?")
    assert res.type == "answer" and ready == ["출장 다녀오면 뭐 해?"]


def test_clarify_route_offers_tasks(monkeypatch, ready):
    monkeypatch.setattr(assistant, "route", lambda q: Route("clarify"))
    res = service.ask(None, "다음에 뭐 해야 해?")
    assert res.type == "clarify"
    assert res.options == service.CLARIFY_OPTIONS
    assert sorted(res.options) == sorted(assistant.TASK_NAMES)
    assert ready == []


def test_answer_route_uses_rag(monkeypatch, ready):
    monkeypatch.setattr(assistant, "route", lambda q: Route("answer"))
    assert service.ask(None, "숙박비 한도?").type == "answer"
    assert ready == ["숙박비 한도?"]


@pytest.mark.parametrize(
    ("question", "task"),
    [
        ("출장 다녀오면 뭘 준비해야 해?", "국내 출장비 정산"),
        ("해외 출장 다녀왔는데 뭐 해?", "국외 출장비 정산"),
        ("법카 쓰고 나서는?", "법인카드 사용 후 처리"),
        ("거래처 접대 후 처리", "업무추진비 집행"),
    ],
)
def test_clarify_with_task_hint_goes_to_procedure(monkeypatch, question, task):
    _pick(monkeypatch, ("ask_which_task", {}))
    assert assistant.route(question) == Route("procedure", task, by="llm+hint")


def test_clarify_without_hint_stays(monkeypatch):
    _pick(monkeypatch, ("ask_which_task", {}))
    assert assistant.route("다음에 뭐 해야 해?") == Route("clarify")
