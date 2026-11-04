"""U-01 규정 Q&A 요청·응답 모양 (docs/API.md 3-1). 바꾸기 전에 프론트 담당에게 먼저 알리기."""

from pydantic import BaseModel, Field, field_validator


class QaRequest(BaseModel):
    question: str = Field(max_length=1000, examples=["출장 때 자가용 쓰면 비용 어떻게 돼요?"])

    @field_validator("question")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("질문을 입력해 주세요.")
        return v


class Source(BaseModel):
    regulation: str  # 여비규정
    article: str  # 제13조 제5항
    revised_at: str | None = None  # U-03 개정일 (YYYY-MM-DD)
    url: str | None = None  # U-03 원문 링크


class QaResponse(BaseModel):
    answer: str
    sources: list[Source]
