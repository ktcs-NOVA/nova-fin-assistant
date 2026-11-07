"""답변 인용 [n] ↔ 출처 목록 정리 테스트 (DB · API 키 없이 실행)."""

from datetime import date
from types import SimpleNamespace

from app.rag.answerer import tidy_citations


def hit(title: str, article: str):
    return SimpleNamespace(
        document=SimpleNamespace(title=title, source_url=None),
        chunk=SimpleNamespace(article=article, revised_at=date(2025, 9, 23)),
        score=0.5,
    )


HITS = [
    hit("여비규정", "제30조"),
    hit("여비규정", "제13조"),
    hit("여비규정", "제13조"),
    hit("여비규정", "제14조"),
]


def test_only_cited_sources_renumbered():
    reply, sources, grounded = tidy_citations("자가용은 승인 필요[2]. 일비는 절반[4].", HITS)
    assert grounded
    assert reply == "자가용은 승인 필요[1]. 일비는 절반[2]."
    assert [(s["ref"], s["article"]) for s in sources] == [(1, "제13조"), (2, "제14조")]
    assert sources[0]["revised_at"] == "2025-09-23"


def test_same_article_chunks_share_number():
    reply, sources, _ = tidy_citations("근거[2][3]", HITS)
    assert reply == "근거[1][1]"
    assert len(sources) == 1


def test_invented_citation_removed():
    reply, sources, grounded = tidy_citations("근거[2], 없는 번호[9]", HITS)
    assert reply == "근거[1], 없는 번호"
    assert grounded and len(sources) == 1


def test_refusal_has_no_sources():
    _, sources, grounded = tidy_citations("담당자 확인이 필요합니다.", HITS)
    assert not grounded and sources == []


def test_no_marks_uses_all_hits():
    _, sources, grounded = tidy_citations("근거 표시 없이 답함", HITS)
    assert grounded and [s["ref"] for s in sources] == [1, 2, 3]
