"""U-01 규정 Q&A 요청·응답 모양 (docs/API.md 3-1). 바꾸기 전에 프론트 담당에게 먼저 알리기."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.domains.procedure.schemas import ProcedureResponse
from app.domains.sources import Source

__all__ = ["QaRequest", "QaResponse", "Source"]


class QaRequest(BaseModel):
    question: str = Field(max_length=1000, examples=["출장 때 자가용 쓰면 비용 어떻게 돼요?"])

    @field_validator("question")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("질문을 입력해 주세요.")
        return v


class QaResponse(BaseModel):
    # answer: 규정 답변 / procedure: 절차 안내 도구의 결과 / clarify: 어떤 업무인지 되묻기
    type: Literal["answer", "procedure", "clarify"] = "answer"
    answer: str
    grounded: bool = True  # False 면 근거를 못 찾은 답변 → 화면에 "담당자 확인 필요" 표시
    sources: list[Source]
    procedure: ProcedureResponse | None = None  # type 이 procedure 일 때 (3-4 와 같은 모양)
    options: list[str] = []  # type 이 clarify 일 때 고를 수 있는 업무
