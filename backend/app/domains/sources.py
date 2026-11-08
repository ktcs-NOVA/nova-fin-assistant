"""여러 기능이 같이 쓰는 근거 조항 모양 (docs/API.md 3-1 의 sources[])."""

from pydantic import BaseModel


class Source(BaseModel):
    ref: int | None = None  # 답변 본문의 [1] 같은 인용 번호와 짝
    regulation: str  # 여비규정
    article: str  # 제13조 제5항
    revised_at: str | None = None  # U-03 개정일 (YYYY-MM-DD)
    url: str | None = None  # U-03 원문 링크
