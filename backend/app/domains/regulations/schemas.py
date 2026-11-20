"""U-03 규정 원문 보기 응답 모양 (docs/API.md 3-9)."""

from pydantic import BaseModel


class RegulationSummary(BaseModel):
    id: int
    title: str  # 여비규정
    revised_at: str | None = None  # 문서 최종 개정일 (YYYY-MM-DD)
    sections: int  # 조문·별표·서식 수


class RegulationSection(BaseModel):
    key: str  # 화면에서 이 조항으로 바로 가기 위한 고유 값 (예: 제14조, 별표 1, 별표#3)
    article: str  # 제14조 / 별표 1 / 별지 제5호 서식
    title: str | None = None  # 일비, 식비, 숙박비
    kind: str  # article(조문) / table(별표) / form(별지 서식)
    chapter: str | None = None  # 제2장 국내여비 (조문만)
    head: str | None = None  # 전결표처럼 같은 '별표'가 여러 구역일 때 구역 이름
    revised_at: str | None = None
    content: str


class RegulationDetail(BaseModel):
    id: int
    title: str
    revised_at: str | None = None
    source_file: str
    sections: list[RegulationSection]
