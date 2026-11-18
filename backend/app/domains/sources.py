"""여러 기능이 같이 쓰는 근거 조항 모양 (docs/API.md 3-1 의 sources[])."""

from pydantic import BaseModel


class Source(BaseModel):
    ref: int | None = None  # 답변 본문의 [1] 같은 인용 번호와 짝
    regulation: str  # 여비규정
    article: str  # 제13조 제5항
    revised_at: str | None = None  # U-03 개정일 (YYYY-MM-DD)
    url: str | None = None  # U-03 원문 링크
    chunk_type: str | None = None  # article(조문) / table(별표) — 규정 Q&A 에서만 채움
    excerpt: str | None = None  # 조항 본문. 출처에 마우스를 올리면 보여 줌 (규정 Q&A 에서만 채움)
