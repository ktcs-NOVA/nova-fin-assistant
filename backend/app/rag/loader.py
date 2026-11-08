"""파일 → 텍스트. 지원: .hwp / .hwpx / .txt / .md

HWPX 는 표의 행·열 정보가 파일에 남아 있어, 표를 한 행씩 뜻이 통하는 줄로 바꿉니다.
    일반 표    구분: 직원(3급 이하) | 식비(1일당): 27 | 숙박비(1일당): 서울 100 / 광역시 90
    전결표     9. 직원복무 > 국내출장 > 부서장을 제외한 직원 → 전결권자: 부서장
    서식(별지) 성  명 | 부서명          ← 제목 줄이 없으므로 칸만 나열
HWP 는 표 구조를 읽지 못해 칸마다 한 줄로 풀립니다.
"""

import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.rag.hwp import read_hwp_text

SUPPORTED = {".hwp", ".hwpx", ".txt", ".md"}

_RE_FORM_START = re.compile(r"^\s*\[별지")
_RE_TABLE_START = re.compile(r"^\s*[\[<]별표")
_RE_SPACED_WORD = re.compile(r"\S(?:\s+\S)+")
APPROVAL_MARK = "○"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _hwpx_paragraph_text(p: ET.Element) -> str:
    """<hp:p> 하나의 글자. 표 안의 문단(중첩된 p)은 따로 처리되므로 건너뜀. 줄바꿈은 \\n 으로."""
    parts: list[str] = []

    def visit(el: ET.Element) -> None:
        for child in el:
            name = _local(child.tag)
            if name == "p":
                continue
            if name == "t":
                parts.append(child.text or "")
                for sub in child:
                    parts.append("\n" if _local(sub.tag) == "lineBreak" else "")
                    parts.append(sub.tail or "")
            else:
                visit(child)

    visit(p)
    return "".join(parts)


@dataclass
class _Cell:
    """표의 칸 하나. 병합된 칸은 격자의 여러 자리가 같은 _Cell 을 가리킵니다."""

    text: str
    row_span: int


def _tidy_cell_part(text: str) -> str:
    """공백을 정리하고, 글자 사이를 벌린 제목을 붙입니다 ('교 통 비' → '교통비')."""
    text = " ".join(text.split())
    if _RE_SPACED_WORD.fullmatch(text) and all(len(w) == 1 for w in text.split()):
        return text.replace(" ", "")
    return text


def _cell_text(tc: ET.Element) -> str:
    """칸 안의 문단을 ' / ' 로 잇습니다. '(1일당)' 같은 괄호 설명은 앞말에 바로 붙입니다."""
    parts: list[str] = []
    for el in tc.iter():
        if _local(el.tag) == "p":
            parts.extend(_tidy_cell_part(x) for x in _hwpx_paragraph_text(el).split("\n"))
    parts = [p for p in parts if p]
    if len(parts) > 1 and all(len(p) == 1 for p in parts):
        return "".join(parts)  # 세로로 쓴 글자 ('인' '사' '팀' → '인사팀')
    text = ""
    for part in parts:
        if not text:
            text = part
        elif part.startswith("("):
            text += part
        else:
            text += f" / {part}"
    return text


def _table_grid(tbl: ET.Element) -> list[list[_Cell | None]]:
    """<hp:tbl> → 2차원 격자. 병합된 칸은 차지하는 자리마다 같은 _Cell 로 채웁니다."""
    placed: dict[tuple[int, int], _Cell] = {}
    rows = cols = 0
    for tr in tbl:
        if _local(tr.tag) != "tr":
            continue
        for tc in tr:
            if _local(tc.tag) != "tc":
                continue
            parts = {_local(x.tag): x for x in tc}
            addr, span = parts["cellAddr"], parts["cellSpan"]
            row, col = int(addr.get("rowAddr", 0)), int(addr.get("colAddr", 0))
            row_span, col_span = int(span.get("rowSpan", 1)), int(span.get("colSpan", 1))
            cell = _Cell(_cell_text(tc), row_span)
            for r in range(row, row + row_span):
                for c in range(col, col + col_span):
                    placed[(r, c)] = cell
            rows, cols = max(rows, row + row_span), max(cols, col + col_span)
    return [[placed.get((r, c)) for c in range(cols)] for r in range(rows)]


def _unique_texts(cells: list[_Cell | None]) -> list[str]:
    """한 행에서 가로로 병합된 칸은 한 번만, 빈 칸은 빼고 글자만 모읍니다."""
    seen: list[_Cell] = []
    for cell in cells:
        if cell is not None and cell.text and not any(cell is s for s in seen):
            seen.append(cell)
    return [c.text for c in seen]


def _approval_lines(grid: list[list[_Cell | None]]) -> list[str]:
    """전결표: ○ 가 있는 칸의 제목(부서장 등)이 전결권자입니다."""
    header = [c.text if c else "" for c in grid[0]]
    first = max(i for i, name in enumerate(header) if name == "세부업무") + 1
    note = header.index("비고")
    lines = []
    for row in grid[1:]:
        if [c.text if c else "" for c in row] == header:
            continue  # 쪽이 넘어가며 반복된 제목 행
        # 좁은 칸에서 줄이 나뉜 글자를 잇습니다 ('재무 / 계 / 약 / 팀', '출장 및 / 여비관리')
        path = " > ".join(
            t.replace(" / ", "" if row[0] is not None and t == row[0].text else " ")
            for t in _unique_texts(row[:first])
        )
        approvers = [
            header[i].replace(" / ", "")
            for i in range(first, note)
            if row[i] is not None and APPROVAL_MARK in row[i].text
        ]
        # 행 전체를 병합한 안내 줄이면 비고 칸도 같은 칸이므로 다시 쓰지 않습니다
        merged_note = any(row[note] is c for c in row[:first])
        remark = row[note].text if row[note] is not None and not merged_note else ""
        line = path
        if approvers:
            line += f" → 전결권자: {', '.join(approvers)}"
        if remark:
            line += f" (비고: {remark})"
        lines.append(line)
    return lines


def _data_lines(grid: list[list[_Cell | None]]) -> list[str]:
    """일반 표: 맨 위 제목 행을 기준으로 각 행을 '제목: 값 | 제목: 값' 으로 씁니다."""
    header_rows = max(c.row_span if c else 1 for c in grid[0])
    if header_rows >= len(grid):
        header_rows = 1
    names = [_unique_texts([grid[r][c] for r in range(header_rows)]) for c in range(len(grid[0]))]
    lines = []
    for row in grid[header_rows:]:
        fields, seen = [], []
        for col, cell in enumerate(row):
            if cell is None or not cell.text or any(cell is s for s in seen):
                continue
            seen.append(cell)
            fields.append(f"{' '.join(names[col])}: {cell.text}")
        if fields:
            lines.append(" | ".join(fields))
    return lines


def _table_lines(tbl: ET.Element, in_form: bool) -> list[str]:
    grid = _table_grid(tbl)
    if not grid or not grid[0]:
        return []
    # 칸이 한 줄뿐이면 표 모양을 빌린 일반 글(제목 상자, 개정 이력 등)
    if len(grid) == 1 or len(grid[0]) == 1:
        return [t for row in grid for cell in row if (t := (cell.text if cell else ""))]
    if in_form:
        return [" | ".join(texts) for row in grid if (texts := _unique_texts(row))]
    header = [c.text if c else "" for c in grid[0]]
    if "세부업무" in header and "비고" in header:
        return _approval_lines(grid)
    return _data_lines(grid)


def read_hwpx_text(path: str | Path) -> str:
    lines: list[str] = []
    in_form = False

    def walk(el: ET.Element) -> None:
        nonlocal in_form
        for child in el:
            name = _local(child.tag)
            if name == "tbl":
                lines.extend(_table_lines(child, in_form))
                continue
            if name == "p":
                text = _hwpx_paragraph_text(child)
                lines.extend(text.split("\n"))
                if _RE_FORM_START.match(text):
                    in_form = True
                elif _RE_TABLE_START.match(text):
                    in_form = False
            walk(child)

    with zipfile.ZipFile(path) as z:
        sections = sorted(
            (n for n in z.namelist() if re.match(r"Contents/section\d+\.xml$", n)),
            key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[-1]).group(1)),
        )
        for name in sections:
            walk(ET.fromstring(z.read(name)))
    return "\n".join(lines)


def load_text(path: str | Path) -> str:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".hwp":
        return read_hwp_text(path)
    if ext == ".hwpx":
        return read_hwpx_text(path)
    if ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8")
    raise ValueError(
        f"지원하지 않는 파일 형식입니다: {path.name} (지원: {', '.join(sorted(SUPPORTED))})"
    )
