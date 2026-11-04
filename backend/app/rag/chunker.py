"""규정 텍스트 → 검색 조각(조 단위).

규정 문서 모양 (한국해양진흥공사 내규 기준):
    머리말        제목, 제정·개정 이력
    본문          제1장 … / 제1조(목적) … ① … 1. …
    부칙          부      칙 <2026. 10. 21.> …     → 건너뜀
    별표 · 별지   [별표 1] 국내여비지급표 …          → 표(table) · 서식(form) 조각

조(條) 하나를 조각 하나로 만들고, 너무 길면 항(①②…) 단위로 나눕니다.
"""

import re
from dataclasses import dataclass, field
from datetime import date

MAX_CHARS = 1500  # 이보다 긴 조는 항 단위로 나눔

# HWP 전용 따옴표 등 깨지는 글자 정리
_CHAR_FIX = {
    "\U000f0852": "“",
    "\U000f0853": "”",
    " ": " ",
    "ⓛ": "①",  # 원문 오타 (영문 l 이 들어간 원문자)
}

_RE_ARTICLE = re.compile(r"^\s*(제\d+조(?:의\d+)?)\s*\(([^)]*)\)\s*(.*)$")
_RE_ARTICLE_DELETED = re.compile(r"^\s*제\d+조(?:의\d+)?\s*삭제")
_RE_CHAPTER = re.compile(r"^\s*(제\d+장)\s+([^<]+?)\s*(?:<.*)?$")
_RE_SUPPLEMENT = re.compile(r"^\s*부\s*칙")
_RE_APPENDIX = re.compile(
    r"^\s*\[(별표\s*\d+(?:의\d+)?|별지\s*제\d+호(?:의\d+)?(?:\s*서식)?)\]\s*(.*)$"
)
_RE_DATE = re.compile(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})")
_RE_HEADER_DATE = re.compile(r"^\s*(?:제정|개정)\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})")
_RE_PARAGRAPH = re.compile(r"^\s*[①-⑳]")


@dataclass
class ChunkDraft:
    seq: int
    chunk_type: str  # article / table / form
    article: str | None
    article_title: str | None
    content: str
    revised_at: date | None = None
    meta: dict = field(default_factory=dict)

    def embed_text(self, regulation: str) -> str:
        """임베딩할 때는 규정명·장 이름을 앞에 붙여 문맥을 더해 줍니다."""
        chapter = self.meta.get("chapter", "")
        return f"[{regulation}] {chapter} {self.content}".strip()


def normalize(text: str) -> str:
    for bad, good in _CHAR_FIX.items():
        text = text.replace(bad, good)
    lines = [ln.rstrip() for ln in text.splitlines()]
    return "\n".join(lines)


def _to_date(m: re.Match) -> date | None:
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def latest_date(text: str) -> date | None:
    """조문 안의 <개정 2025. 9. 23., 2026. 10. 21.> 같은 표시 중 가장 최근 날짜."""
    dates = [d for m in _RE_DATE.finditer(text) if (d := _to_date(m))]
    return max(dates) if dates else None


def document_revised_at(text: str) -> date | None:
    """머리말의 '제정/개정 YYYY. M. D.' 중 가장 최근 날짜 = 문서 최종 개정일."""
    dates = [
        d
        for ln in text.splitlines()[:40]
        if (m := _RE_HEADER_DATE.match(ln)) and (d := _to_date(m))
    ]
    return max(dates) if dates else None


def _split_long(body: list[str]) -> list[list[str]]:
    """긴 조를 항(①②…) 단위로 나눔. 첫 줄(조 제목 줄)은 각 조각에 붙여 문맥 유지."""
    if sum(len(x) for x in body) <= MAX_CHARS:
        return [body]
    head, parts, cur = body[0], [], [body[0]]
    for ln in body[1:]:
        if _RE_PARAGRAPH.match(ln) and sum(len(x) for x in cur) > MAX_CHARS // 2:
            parts.append(cur)
            cur = [head + " (계속)", ln]
        else:
            cur.append(ln)
    parts.append(cur)
    return parts


def split_regulation(text: str) -> list[ChunkDraft]:
    text = normalize(text)
    drafts: list[ChunkDraft] = []

    chapter = ""
    mode = "body"  # body / supplement / appendix
    cur: dict | None = None  # 지금 모으는 조각

    def flush() -> None:
        nonlocal cur
        if not cur:
            return
        lines = [ln for ln in cur["lines"] if ln.strip()]
        cur_ = cur
        cur = None
        if not lines:
            return
        if cur_["type"] == "article":
            groups = _split_long(lines)
        else:
            groups = [lines]
        for i, g in enumerate(groups):
            content = "\n".join(g).strip()
            meta = {"chapter": cur_.get("chapter", "")}
            if len(groups) > 1:
                meta["part"] = i + 1
            drafts.append(
                ChunkDraft(
                    seq=len(drafts),
                    chunk_type=cur_["type"],
                    article=cur_["article"],
                    article_title=cur_["title"],
                    content=content,
                    revised_at=latest_date(content),
                    meta=meta,
                )
            )

    for line in text.splitlines():
        # --- 별표 · 별지 시작 (어느 모드에서든) ---
        if m := _RE_APPENDIX.match(line):
            flush()
            mode = "appendix"
            label = re.sub(r"\s+", " ", m.group(1))
            rest = m.group(2).strip()
            if rest.startswith("삭제"):
                continue  # 삭제된 별표는 버림
            title = re.sub(r"<.*", "", rest).strip() or None
            cur = {
                "type": "form" if label.startswith("별지") else "table",
                "article": label,
                "title": title,
                "lines": [line.strip()],
            }
            continue

        if mode == "appendix":
            if cur is not None:
                cur["lines"].append(line)
            continue

        # --- 부칙 (본문이 끝난 뒤, 별표 전까지) ---
        if _RE_SUPPLEMENT.match(line):
            flush()
            mode = "supplement"
            continue
        if mode == "supplement":
            continue

        # --- 본문 ---
        if m := _RE_CHAPTER.match(line):
            flush()
            chapter = f"{m.group(1)} {m.group(2).strip()}"
            continue
        if _RE_ARTICLE_DELETED.match(line):
            flush()
            continue
        if m := _RE_ARTICLE.match(line):
            flush()
            cur = {
                "type": "article",
                "article": m.group(1),
                "title": m.group(2).strip(),
                "chapter": chapter,
                "lines": [line.strip()],
            }
            continue
        if cur is not None:
            cur["lines"].append(line)

    flush()
    return drafts
