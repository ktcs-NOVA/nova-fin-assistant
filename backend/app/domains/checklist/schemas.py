"""체크리스트 응답 모양 (docs/API.md 3-3)."""

from pydantic import BaseModel


class ChecklistItem(BaseModel):
    id: int
    text: str
    basis: str


class ChecklistResponse(BaseModel):
    type: str
    items: list[ChecklistItem]
