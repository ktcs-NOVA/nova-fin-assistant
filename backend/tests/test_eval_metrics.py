"""평가 지표 계산 테스트 (scripts/eval_qa.py) — DB·API 없이 돌아갑니다."""

from scripts.eval_qa import contains_required, group_report

JOB = "여비규정 제11조"
OTHER = "여비규정 제10조"


def _row(group: str, top1: str, cited: str | None = None, expected: str = JOB) -> dict:
    row = {"id": "1", "question": "질문", "group": group, "top1": top1, "expected": expected}
    if cited is not None:
        row["cited"] = cited
    return row


def test_contains_required_or_and():
    assert contains_required("식비의 3분의 1을 차감합니다", "3분의 1|1/3")
    assert contains_required("청구서와 영수증을 냅니다", "청구서;영수증")
    assert not contains_required("영수증만 냅니다", "청구서;영수증")


def test_contains_required_ignores_spaces_and_thousand_commas():
    assert contains_required("하루 27,000원입니다", "27000|27천원")
    assert contains_required("식비의 3분의1 차감", "3분의 1")
    assert not contains_required("1일당 80,000원입니다", "27000|27천원")


def test_group_consistent_when_all_cite_expected_article():
    rows = [
        _row("숙박", JOB, JOB),
        _row("숙박", OTHER, f"{OTHER} | {JOB}"),
        _row("", OTHER, OTHER),  # 그룹 없는 질문은 제외
    ]
    [g] = group_report(rows)
    assert (g["group"], g["size"]) == ("숙박", 2)
    assert g["same_top1"] == 0
    assert g["same_cited"] == 1


def test_group_inconsistent_when_one_answer_differs_or_has_no_source():
    assert group_report([_row("숙박", JOB, JOB), _row("숙박", JOB, OTHER)])[0]["same_cited"] == 0
    assert group_report([_row("숙박", JOB, JOB), _row("숙박", JOB, "")])[0]["same_cited"] == 0


def test_group_common_article_must_be_the_expected_one():
    rows = [_row("숙박", OTHER, OTHER), _row("숙박", OTHER, OTHER)]
    assert group_report(rows)[0]["same_cited"] == 0


def test_group_retrieval_only_has_no_cited_score():
    [g] = group_report([_row("숙박", JOB), _row("숙박", JOB)])
    assert g["same_top1"] == 1
    assert g["same_cited"] == ""
