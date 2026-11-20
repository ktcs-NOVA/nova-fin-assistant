"""U-03 규정 원문 보기: 나뉜 조각을 원문 순서대로 다시 잇는지 (DB · API 키 없이 실행)."""

from datetime import date
from types import SimpleNamespace

from app.domains.regulations.service import build_sections


def chunk(article, content, chunk_type="article", title=None, chapter=None):
    return SimpleNamespace(
        article=article,
        article_title=title,
        chunk_type=chunk_type,
        content=content,
        revised_at=date(2025, 9, 23),
        meta={"chapter": chapter} if chapter else {},
    )


def test_split_article_is_joined_without_repeated_head():
    sections = build_sections(
        [
            chunk(
                "제14조",
                "제14조(일비, 식비, 숙박비) ① 일비는 정액\n② 숙박비는 실비",
                title="일비, 식비, 숙박비",
                chapter="제2장 국내여비",
            ),
            chunk(
                "제14조",
                "제14조(일비, 식비, 숙박비) (계속)\n③ 전일 출발\n④ 장기 체류",
                title="일비, 식비, 숙박비",
                chapter="제2장 국내여비",
            ),
            chunk(
                "제15조",
                "제15조(여비보조시의 여비지급) ① 보조금 차감",
                title="여비보조시의 여비지급",
            ),
        ]
    )
    assert [s["key"] for s in sections] == ["제14조", "제15조"]
    first = sections[0]
    assert first["content"].splitlines() == [
        "제14조(일비, 식비, 숙박비) ① 일비는 정액",
        "② 숙박비는 실비",
        "③ 전일 출발",
        "④ 장기 체류",
    ]
    assert first["chapter"] == "제2장 국내여비" and first["revised_at"] == "2025-09-23"


def test_long_table_parts_are_joined():
    sections = build_sections(
        [
            chunk("별표 1", "[별표 1] 국내여비지급표\n구분: 사장 | 일비: 30", "table"),
            chunk("별표 1", "[별표 1] 국내여비지급표 (계속)\n구분: 직원 | 일비: 30", "table"),
        ]
    )
    assert len(sections) == 1
    assert sections[0]["content"].splitlines() == [
        "[별표 1] 국내여비지급표",
        "구분: 사장 | 일비: 30",
        "구분: 직원 | 일비: 30",
    ]


def test_approval_table_groups_by_section_and_keeps_notes_once():
    head = "<별표> 1. 전사 공통 사항 · 가. 일반"
    sections = build_sections(
        [
            chunk(
                "별표",
                f"{head}\n9. 직원복무 > 국내출장 → 전결권자: 부서장\n※ 사장직속 부서는 상임이사",
                "table",
            ),
            chunk(
                "별표",
                f"{head}\n10. 교육 > 교육 신청 → 전결권자: 팀장\n※ 사장직속 부서는 상임이사",
                "table",
            ),
            chunk(
                "별표",
                "<별표> 3. 경영기획본부 · 나. 인사총무부\n인사팀 > 국내 여비 → 전결권자: 팀장",
                "table",
            ),
        ]
    )
    assert [s["key"] for s in sections] == ["별표#1", "별표#2"]
    assert sections[0]["head"] == "1. 전사 공통 사항 · 가. 일반"
    assert sections[0]["content"].splitlines() == [
        head,
        "9. 직원복무 > 국내출장 → 전결권자: 부서장",
        "10. 교육 > 교육 신청 → 전결권자: 팀장",
        "※ 사장직속 부서는 상임이사",  # 조각마다 반복되던 안내는 끝에 한 번만
    ]
