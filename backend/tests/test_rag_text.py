"""문서 읽기 · 조 단위 분할 · 마스킹 테스트 (DB · API 키 없이 실행)."""

import zipfile
from datetime import date
from pathlib import Path

import pytest

from app.ai.masking import mask
from app.rag.chunker import MAX_CHARS, document_revised_at, split_regulation
from app.rag.loader import load_text

REG_DIR = Path(__file__).resolve().parents[1] / "data" / "regulations"
TRAVEL = REG_DIR / "여비규정(2026년도 10월 21일 개정).hwpx"
DELEGATION = REG_DIR / "위임전결규정 시행세칙(2026년도 6월 22일 개정).hwpx"


def _cell(row: int, col: int, text: str, row_span: int = 1, col_span: int = 1) -> str:
    paragraphs = "".join(f"<hp:p><hp:run><hp:t>{t}</hp:t></hp:run></hp:p>" for t in text.split("|"))
    return (
        f"<hp:tc><hp:subList>{paragraphs}</hp:subList>"
        f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/>'
        f'<hp:cellSpan colSpan="{col_span}" rowSpan="{row_span}"/></hp:tc>'
    )


def _table(*rows: list[str]) -> str:
    body = "".join(f"<hp:tr>{''.join(cells)}</hp:tr>" for cells in rows)
    return f"<hp:p><hp:run><hp:tbl>{body}</hp:tbl></hp:run></hp:p>"


def _hwpx(tmp_path: Path, *blocks: str) -> Path:
    """표 XML 로 작은 HWPX 파일을 만듭니다. 문자열 블록은 일반 문단입니다."""
    body = "".join(b if b.startswith("<") else f"<hp:p><hp:t>{b}</hp:t></hp:p>" for b in blocks)
    path = tmp_path / "test.hwpx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Contents/section0.xml", f'<sec xmlns:hp="urn:hp">{body}</sec>')
    return path


def _lines(path: Path) -> list[str]:
    """빈 줄을 뺀 줄 목록 (표를 담은 문단은 빈 줄을 하나 남김)."""
    return [ln for ln in load_text(path).splitlines() if ln]


def test_hwpx_table_uses_header_and_merged_cells(tmp_path):
    # 2단 제목 + 세로 병합 칸: 칸마다 제목이 붙고, 병합된 값은 모든 행에 채워짐
    table = _table(
        [_cell(0, 0, "구    분", row_span=2), _cell(0, 1, "교 통 비", col_span=2), _cell(0, 3, "식 비|(1일당)", row_span=2)],
        [_cell(1, 1, "항공"), _cell(1, 2, "철도")],
        [_cell(2, 0, "직원"), _cell(2, 1, "실비", col_span=2), _cell(2, 3, "27", row_span=2)],
        [_cell(3, 0, "임원"), _cell(3, 1, "특실"), _cell(3, 2, "일반")],
    )
    lines = _lines(_hwpx(tmp_path, "앞 문단", table, "뒤 문단"))
    assert lines == [
        "앞 문단",
        "구분: 직원 | 교통비 항공: 실비 | 식비(1일당): 27",
        "구분: 임원 | 교통비 항공: 특실 | 교통비 철도: 일반 | 식비(1일당): 27",
        "뒤 문단",
    ]


def test_hwpx_table_keeps_lines_inside_a_cell_apart(tmp_path):
    table = _table(
        [_cell(0, 0, "구분"), _cell(0, 1, "숙박비")],
        [_cell(1, 0, "직원"), _cell(1, 1, "서울 100|광역시 90")],
    )
    assert _lines(_hwpx(tmp_path, table)) == ["구분: 직원 | 숙박비: 서울 100 / 광역시 90"]


def test_hwpx_form_table_lists_cells_without_headers(tmp_path):
    table = _table([_cell(0, 0, "성명"), _cell(0, 1, "부서")], [_cell(1, 0, "금액"), _cell(1, 1, "")])
    lines = _lines(_hwpx(tmp_path, "[별지 제1호 서식] 출장원", table))
    assert lines == ["[별지 제1호 서식] 출장원", "성명 | 부서", "금액"]


def test_hwpx_layout_table_stays_plain_text(tmp_path):
    table = _table([_cell(0, 0, "제정 2020. 1. 1.")], [_cell(1, 0, "개정 2024. 5. 6.")])
    path = _hwpx(tmp_path, table)
    assert _lines(path) == ["제정 2020. 1. 1.", "개정 2024. 5. 6."]
    assert document_revised_at(load_text(path)) == date(2024, 5, 6)


def _approval_table() -> str:
    head = ["기본업무", "세부업무", "세부업무", "부서장", "본부장", "상임|이사", "비고"]
    return _table(
        [
            _cell(0, 0, "기본업무"),
            _cell(0, 1, "세부업무", col_span=2),
            _cell(0, 3, head[3]),
            _cell(0, 4, head[4]),
            _cell(0, 5, head[5]),
            _cell(0, 6, head[6]),
        ],
        [
            _cell(1, 0, "9. 직원복무", row_span=3),
            _cell(1, 1, "국내출장", row_span=2),
            _cell(1, 2, "부서장|이외 직원"),
            _cell(1, 3, "○"),
            _cell(1, 4, ""),
            _cell(1, 5, ""),
            _cell(1, 6, ""),
        ],
        [
            _cell(2, 2, "부서장"),
            _cell(2, 3, ""),
            _cell(2, 4, "○"),
            _cell(2, 5, ""),
            _cell(2, 6, ""),
        ],
        [
            _cell(3, 1, "국외출장"),
            _cell(3, 2, "감사"),
            _cell(3, 3, ""),
            _cell(3, 4, ""),
            _cell(3, 5, "○"),
            _cell(3, 6, "협조"),
        ],
    )


def test_hwpx_approval_table_finds_approver_column(tmp_path):
    assert _lines(_hwpx(tmp_path, _approval_table())) == [
        "9. 직원복무 > 국내출장 > 부서장 이외 직원 → 전결권자: 부서장",
        "9. 직원복무 > 국내출장 > 부서장 → 전결권자: 본부장",
        "9. 직원복무 > 국외출장 > 감사 → 전결권자: 상임이사 (비고: 협조)",
    ]


def test_angle_bracket_appendix_splits_by_section_and_task():
    chunks = split_regulation(
        "\n".join(
            [
                "제1조(목적) 전결 기준을 정한다.",
                "<별표> <개정 2025. 2. 6., 2026. 6. 22.>",
                "1. 전사 공통 사항",
                " 가. 일반",
                "9. 직원복무 > 국내출장 → 전결권자: 부서장",
                "10. 교육 > 교육 신청 → 전결권자: 팀장",
                "※ 공통 안내",
                " 나. 인사총무부",
                "인사팀 > 5. 여비관리 > 국내 여비 → 전결권자: 팀장",
            ]
        )
    )
    tables = [c for c in chunks if c.chunk_type == "table"]
    assert chunks[0].article == "제1조"
    assert {c.article for c in tables} == {"별표"}
    assert [c.content for c in tables] == [
        "<별표> 1. 전사 공통 사항 · 가. 일반\n9. 직원복무 > 국내출장 → 전결권자: 부서장\n※ 공통 안내",
        "<별표> 1. 전사 공통 사항 · 가. 일반\n10. 교육 > 교육 신청 → 전결권자: 팀장\n※ 공통 안내",
        "<별표> 1. 전사 공통 사항 · 나. 인사총무부\n인사팀 > 5. 여비관리 > 국내 여비 → 전결권자: 팀장",
    ]
    assert all(c.revised_at == date(2026, 6, 22) for c in tables)  # 머리 줄의 개정일 유지


def test_long_table_splits_on_rows_and_keeps_head():
    rows = [f"구분: {i} | 금액: {'9' * 100}" for i in range(40)]
    chunks = split_regulation("\n".join(["[별표 3] 지급표 <개정 2024. 1. 10.>", *rows]))
    assert len(chunks) > 1
    assert all(len(c.content) <= MAX_CHARS + 50 for c in chunks)
    assert all(c.content.startswith("[별표 3] 지급표") for c in chunks)
    assert sum(c.content.count("구분:") for c in chunks) == 40
    assert all(c.revised_at == date(2024, 1, 10) for c in chunks)


@pytest.mark.skipif(not TRAVEL.exists(), reason="규정 파일 없음")
def test_travel_allowance_table_reads_by_grade():
    text = load_text(TRAVEL)
    row = next(ln for ln in text.splitlines() if ln.startswith("구분: 직원(3급 이하)"))
    assert "식비(1일당): 27" in row
    assert "숙박비(1일당): 서울 100 / 광역시 90 / 기타 80" in row


@pytest.mark.skipif(not DELEGATION.exists(), reason="규정 파일 없음")
def test_delegation_table_is_chunked_with_approvers():
    text = load_text(DELEGATION)
    assert document_revised_at(text) == date(2026, 6, 22)
    chunks = [c for c in split_regulation(text) if c.chunk_type == "table"]
    domestic = next(c for c in chunks if "국내출장" in c.content)
    assert "9. 직원복무 > 국내출장 > 부서장을 제외한 직원 → 전결권자: 부서장" in domestic.content
    assert "9. 직원복무 > 국내출장 > 개방형 본부장 → 전결권자: 상임이사" in domestic.content
    assert domestic.revised_at == date(2026, 6, 22)
    assert any("인사팀 > 5. 여비관리" in c.content for c in chunks)


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
