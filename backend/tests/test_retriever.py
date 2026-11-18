"""하이브리드 검색 부품 테스트 (DB · API 키 없이 실행)."""

from types import SimpleNamespace

from app.rag.retriever import KeywordIndex, bigrams, diversify, fuse
from app.rag.synonyms import expand


def hit(title: str, article: str, chunk_id: int):
    return SimpleNamespace(
        document=SimpleNamespace(title=title),
        chunk=SimpleNamespace(article=article, id=chunk_id),
        score=0.5,
    )


def test_expand_adds_regulation_terms():
    assert "법인카드" in expand("법카로 노래방 가도 돼?")
    assert "레저업종" in expand("법카로 노래방 가도 돼?")
    assert "업무추진비" in expand("회의비에 참석자를 꼭 적어야 하나요?")
    assert "총인원수" in expand("회의비에 참석자를 꼭 적어야 하나요?")
    assert "자가용" in expand("마이카로 출장 가도 돼?")


def test_expand_ignores_spacing_and_keeps_plain_question():
    assert "자가용" in expand("내 차로 출장 가도 돼?")
    assert expand("출장 일비는 얼마예요?") == "출장 일비는 얼마예요?"


def test_bigrams_stay_inside_words():
    assert bigrams("노래방!") == ["노래", "래방"]
    assert bigrams("출장 때") == ["출장"]  # 낱말 경계를 넘는 '장때'는 만들지 않음
    assert "23" in bigrams("23시～익일")


def test_keyword_index_finds_exact_word():
    index = KeywordIndex.build(
        [
            (1, "출장 일비는 정액으로 지급한다"),
            (2, "레저업종: 골프장, 노래방, 당구장"),
            (3, "출장 숙박비는 실비로 지급한다"),
        ]
    )
    assert index.search("노래방 가도 돼?", 3)[0] == 2
    assert index.search("아무 관련 없는 질문", 3) == []


def test_fuse_prefers_chunks_ranked_by_both():
    assert fuse([1, 2, 3], [3, 4, 1])[:2] == [1, 3]


def test_diversify_limits_chunks_per_article():
    hits = [hit("위임전결규정 시행세칙", "별표", i) for i in range(5)]
    hits += [hit("업무추진비 지침", "제8조", 10), hit("여비규정", "제13조", 11)]
    picked = diversify(hits, 5, per_article=2)
    assert [h.chunk.id for h in picked] == [0, 1, 10, 11]
