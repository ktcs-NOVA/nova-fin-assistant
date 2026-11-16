"""문서 작업 요청/응답 모양 (docs/API.md 3-11)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Kind = Literal["출장보고서", "회의록", "출장원", "지출결과서"]
_MAX_TEXT = 5000
_MAX_LIST = 100


def _clean_fields(v: dict[str, Any]) -> dict[str, Any]:
    """문자·숫자·문자 목록만 받고 길이를 제한합니다 (JSON 통째로 저장하기 때문)."""
    out: dict[str, Any] = {}
    for key, val in v.items():
        if not isinstance(key, str) or len(key) > 40:
            raise ValueError("입력 항목 이름이 올바르지 않습니다.")
        if val is None or isinstance(val, bool | int | float):
            out[key] = val
        elif isinstance(val, str):
            if len(val) > _MAX_TEXT:
                raise ValueError(f"'{key}' 내용이 너무 깁니다 ({_MAX_TEXT}자 이하).")
            out[key] = val
        elif (
            isinstance(val, list)
            and len(val) <= _MAX_LIST
            and all(isinstance(x, str) and len(x) <= 50 for x in val)
        ):
            out[key] = val
        else:
            raise ValueError(f"'{key}' 값 형식이 올바르지 않습니다.")
    return out


class DocumentCreate(BaseModel):
    kind: Kind
    title: str | None = Field(default=None, max_length=100)
    fields: dict[str, Any] = Field(default_factory=dict)
    # 이 서류가 붙을 정산 건 번호 (S-2026-001). 지출결과서는 꼭 있어야 합니다.
    submission_code: str | None = Field(default=None, max_length=20)

    _clean = field_validator("fields")(_clean_fields)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    fields: dict[str, Any] | None = None
    draft: str | None = Field(default=None, max_length=20000)
    confirmed: bool | None = None

    @field_validator("fields")
    @classmethod
    def _clean(cls, v):
        return None if v is None else _clean_fields(v)


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    status: str
    fields: dict[str, Any]
    draft: str
    confirmed: bool
    submission_code: str | None = None
    sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SubmissionDocument(BaseModel):
    """관리자 화면: 정산 건에 붙어 온 서류 한 건."""

    id: int
    kind: str
    title: str
    writer: str
    sent_at: datetime
    draft: str = ""
    form: dict[str, Any] | None = None  # 지출결과서면 양식(두 장), 나머지는 draft 본문


class SubmissionDocuments(BaseModel):
    expected: list[str]  # 이 정산 유형에서 받아야 하는 서류 종류
    missing: list[str]  # 그중 아직 안 온 것
    documents: list[SubmissionDocument]
