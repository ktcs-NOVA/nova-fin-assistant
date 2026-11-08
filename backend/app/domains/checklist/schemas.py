"""체크리스트 요청·응답 모양 (docs/API.md 3-3, 3-5). 바꾸기 전에 프론트 담당에게 먼저 알리기."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains.procedure.schemas import Fact
from app.domains.sources import Source


class ChecklistItem(BaseModel):
    id: int
    text: str
    basis: str


class ChecklistResponse(BaseModel):
    type: str
    items: list[ChecklistItem]


class SavedChecklistCreate(BaseModel):
    task: str = Field(max_length=100, examples=["국내 출장비 정산"])

    @field_validator("task")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("저장할 업무를 알려 주세요.")
        return v


class SavedChecklistItemUpdate(BaseModel):
    done: bool


class SavedChecklistItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: Literal["document", "step"]  # 필요 서류 / 작성 순서
    title: str
    detail: str
    basis: str
    done: bool
    done_at: datetime | None


class SavedChecklist(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task: str
    summary: str
    deadline: Fact | None
    approver: Fact | None
    sources: list[Source]
    created_at: datetime
    items: list[SavedChecklistItem]
