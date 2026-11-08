"""U-02 업무절차 안내 테스트 — DB·API 키 없이 실행."""

import re
from pathlib import Path

import pytest

from app.domains.procedure.service import (
    Article,
    approver_text,
    build_response,
    missing_cites,
    task_cites,
)
from app.domains.procedure.tasks import BUSINESS, CARD, TASKS, TRAVEL, match_task
from app.rag.chunker import split_regulation
from app.rag.loader import load_text

REG_DIR = Path(__file__).resolve().parents[1] / "data" / "regulations"
TASK = {t.name: t for t in TASKS}
APPROVER = {
    "text": "부서장을 제외한 직원: 부서장",
    "basis": "위임전결규정 시행세칙 별표",
    "check": False,
}
APPROVER_SOURCE = Article("위임전결규정 시행세칙", "별표", "")
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def _regulation_articles() -> dict[tuple[str, str], Article]:
    """실제 규정 파일을 읽어 (규정명, 조항) → 조항 글자로 만듭니다."""
    articles: dict[tuple[str, str], Article] = {}
    for regulation in (TRAVEL, CARD, BUSINESS):
        path = next(REG_DIR.glob(f"{regulation}(*.hwpx"), None)
        if path is None:
            pytest.skip("규정 파일 없음")
        for chunk in split_regulation(load_text(path)):
            key = (regulation, chunk.article or "")
            before = articles[key].content if key in articles else ""
            articles[key] = Article(
                regulation, key[1], f"{before}\n{chunk.content}", chunk.revised_at
            )
    return articles


def _fake_articles(task) -> dict[tuple[str, str], Article]:
    """근거 표현을 모두 담은 가짜 조항. 규정 파일 없이 응답 조립만 검사합니다."""
    articles: dict[tuple[str, str], Article] = {}
    for cite in task_cites(task):
        key = (cite.regulation, cite.article)
        before = articles[key].content if key in articles else ""
        articles[key] = Article(cite.regulation, cite.article, f"{before} {cite.phrase}")
    return articles


def _all_text(data: dict) -> str:
    items = [*data["documents"], *data["steps"], data["deadline"]]
    return data["summary"] + " ".join(
        f"{x.get('name', '')} {x.get('title', '')} {x.get('detail', '')} {x.get('text', '')}"
        for x in items
    )


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("국내 출장비 정산하려면?", "국내 출장비 정산"),
        ("출장비 정산 어떻게 해?", "국내 출장비 정산"),
        ("해외 출장 다녀왔는데 비용 정산 절차 알려줘", "국외 출장비 정산"),
        ("법인카드 쓰고 나서 처리할 일은?", "법인카드 사용 후 처리"),
        ("법카 결제하고 뭐 해야 돼?", "법인카드 사용 후 처리"),
        ("업무추진비 집행 절차는?", "업무추진비 집행"),
    ],
)
def test_match_task(question, expected):
    assert match_task(question).name == expected


@pytest.mark.parametrize(
    "question", ["연차 신청 절차 알려줘", "법인카드 분실하면 어떻게 처리해?", "출장 승인받으려면?"]
)
def test_unknown_task_is_not_matched(question):
    assert match_task(question) is None


def test_every_cite_is_in_the_current_regulation():
    """규정 파일과 절차 내용이 어긋나면 실패합니다. 규정이 개정되면 tasks.py 를 함께 고치세요."""
    articles = _regulation_articles()
    for task in TASKS:
        assert [c.label for c in missing_cites(task, articles)] == [], task.name


def test_every_cited_paragraph_contains_its_phrase():
    """'제2항' 근거의 표현이 정말 ②에 있는지 확인합니다."""
    articles = _regulation_articles()
    for task in TASKS:
        for cite in task_cites(task):
            if not cite.paragraph:
                continue
            number = int(re.fullmatch(r"제(\d+)항", cite.paragraph)[1])
            parts = re.split(f"([{CIRCLED}])", articles[(cite.regulation, cite.article)].content)
            marks = parts[1::2]
            bodies = parts[2::2]
            body = bodies[marks.index(CIRCLED[number - 1])]
            assert "".join(cite.phrase.split()) in "".join(body.split()), cite.label


def test_response_has_only_cited_sources_and_basis():
    task = TASK["국내 출장비 정산"]
    data = build_response(task, _fake_articles(task), APPROVER, APPROVER_SOURCE)
    assert data["grounded"] is True
    assert data["approver"] == APPROVER
    assert [s["ref"] for s in data["sources"]] == list(range(1, len(data["sources"]) + 1))
    assert data["sources"][-1]["article"] == "별표"
    report = next(d for d in data["documents"] if d["name"] == "출장보고서")
    assert report["basis"] == "여비규정 별지 제4호 서식"
    receipt = next(d for d in data["documents"] if "영수증" in d["name"])
    assert receipt["basis"] == "여비규정 제10조 제1항, 제10조 제2항, 제10조 제3항"


def test_revised_regulation_is_not_answered_with_old_content():
    task = TASK["국내 출장비 정산"]
    articles = _fake_articles(task)
    articles[(TRAVEL, "제3조의2")].content = "개정되어 기한 표현이 바뀐 조항"
    data = build_response(task, articles, APPROVER, APPROVER_SOURCE)
    assert data["grounded"] is False
    assert data["steps"] == [] and data["sources"] == [] and data["approver"] is None
    assert "담당자 확인" in data["summary"]


def test_trip_guides_receipts_and_deadline():
    task = TASK["국내 출장비 정산"]
    data = build_response(task, _fake_articles(task), APPROVER, APPROVER_SOURCE)
    names = " ".join(d["name"] for d in data["documents"])
    assert all(word in names for word in ("출장원(정산)", "출장보고서", "영수증", "숙박시설"))
    assert "15일 이내" in data["deadline"]["text"]


def test_overseas_trip_guides_preparation_money():
    task = TASK["국외 출장비 정산"]
    text = _all_text(build_response(task, _fake_articles(task), APPROVER, APPROVER_SOURCE))
    assert "준비금" in text and "마일리지" in text


def test_business_expense_limits_conditions_to_their_targets():
    task = TASK["업무추진비 집행"]
    data = build_response(task, _fake_articles(task), APPROVER, APPROVER_SOURCE)
    text = _all_text(data)
    assert "100만원" in text and "일상감사" in text
    assert "임원은 당월 사용실적을 익월 8영업일" in data["deadline"]["text"]
    assert data["deadline"]["check"] is True  # 임원 외 기한은 지침에 없음


def test_card_separates_who_files_the_expense():
    task = TASK["법인카드 사용 후 처리"]
    text = _all_text(build_response(task, _fake_articles(task), APPROVER, APPROVER_SOURCE))
    assert "팀별로 배부된 카드는 사용직원이" in text
    assert "부서장 이상에게 배부된 카드는 관리부서에서" in text


def test_approver_text_reads_rows_and_exception():
    content = "\n".join(
        [
            "<별표> 1. 전사 공통 사항 · 가. 일반",
            "9. 직원복무 > 국내출장 > 감사 (비고: 감사)",
            "9. 직원복무 > 국내출장 > 부서장 → 전결권자: 본부장",
            "9. 직원복무 > 국내출장 > 부서장을 제외한 직원 → 전결권자: 부서장",
            "9. 직원복무 > 국외출장 > 부서장 이상의 임직원 → 전결권자: 상임이사",
            "※ 사장직속 부서의 본부장 전결사항은 상임이사가 결재한다.",
            "※ 다른 안내",
        ]
    )
    assert approver_text([content], "9. 직원복무 > 국내출장") == (
        "감사: 감사 / 부서장: 본부장 / 부서장을 제외한 직원: 부서장 "
        "※ 사장직속 부서의 본부장 전결사항은 상임이사가 결재한다."
    )


def test_approver_text_trims_subject_and_handles_no_row():
    row = "11. 집행 결의 > 부서·부서장 집행 결의 → 전결권자: 부서장"
    assert approver_text([row], "11. 집행 결의", " 집행 결의") == "부서·부서장: 부서장"
    assert approver_text([row], "없는 업무") == ""
