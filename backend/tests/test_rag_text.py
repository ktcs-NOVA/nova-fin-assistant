"""문서 읽기 · 조 단위 분할 · 마스킹 테스트 (DB · API 키 없이 실행)."""

from datetime import date
from pathlib import Path

import pytest

from app.ai.masking import mask
from app.rag.chunker import document_revised_at, split_regulation
from app.rag.loader import load_text

REG_DIR = Path(__file__).resolve().parents[1] / "data" / "regulations"
TRAVEL = REG_DIR / "여비규정(2026.10.21).hwp"


@pytest.mark.skipif(not TRAVEL.exists(), reason="규정 파일 없음")
def test_travel_regulation_split():
    text = load_text(TRAVEL)
    assert document_revised_at(text) == date(2026, 10, 21)

    chunks = split_regulation(text)
    articles = [c.article for c in chunks if c.chunk_type == "article"]
    assert articles[0] == "제1조" and articles[-1] == "제45조"
    assert len(articles) == len(set(articles))  # 부칙의 제1조 등이 섞이지 않음

    art14 = next(c for c in chunks if c.article == "제14조")
    assert art14.article_title == "일비, 식비, 숙박비"
    assert art14.revised_at == date(2026, 10, 21)
    assert art14.meta["chapter"] == "제2장 국내여비"

    tables = [c.article for c in chunks if c.chunk_type == "table"]
    assert "별표 1" in tables and "별표 2" not in tables  # 삭제된 별표 제외


def test_split_skips_supplementary_provisions():
    text = "\n".join(
        [
            "테스트 규정",
            "제정 2020. 1. 1.",
            "개정 2024. 5. 6.",
            "제1조(목적) 이 규정은 테스트를 위한 것이다.",
            "제2조(정의) ① 첫째 항 <개정 2024. 5. 6.>",
            "  ② 둘째 항",
            "제3조 삭제 <2023. 1. 1.>",
            "   부      칙 <2020. 1. 1.>",
            "제1조(시행일) 이 규정은 2020년 1월 1일부터 시행한다.",
            "[별표 1] 지급표",
            "구분 금액",
        ]
    )
    chunks = split_regulation(text)
    assert [c.article for c in chunks] == ["제1조", "제2조", "별표 1"]
    assert chunks[1].revised_at == date(2024, 5, 6)
    assert document_revised_at(text) == date(2024, 5, 6)


def test_mask_personal_info():
    s = "카드 1234-5678-9012-3456, 연락처 010-1234-5678, 사용일 2026-10-20"
    out = mask(s)
    assert "1234-5678-9012-3456" not in out
    assert "010-1234-5678" not in out
    assert "2026-10-20" in out  # 날짜는 그대로
