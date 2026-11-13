"""정산 제출(직원) · 검토 대기함(관리자, M-01) 요청·응답 모양.

응답 한 건의 모양은 프론트 목업 frontend/src/mocks/submissions.json 의 한 건과 같습니다.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class SubmissionCreate(BaseModel):
    """직원이 청구 검증(U-04)을 마친 내역을 제출. /api/verify 요청과 같은 모양 + 아래 선택 필드."""

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "trip_type": "국내출장",
                    "grade": "직원 3급 이하",
                    "trip": {"start_date": "2026-10-20", "end_date": "2026-10-21", "region": "부산"},
                    "items": [
                        {"field": "철도운임", "amount": 59800, "date": "2026-10-20", "seat_class": "일반"},
                        {"field": "숙박비", "amount": 88000, "date": "2026-10-20", "nights": 1, "breakfast_included": True},
                    ],
                    "purpose": "부산 선사 방문 출장 여비",
                    "account": "여비교통비",
                }
            ]
        },
    )

    trip_type: str = "국내출장"
    grade: str = "직원 3급 이하"
    trip: dict[str, Any] | None = None
    items: list[dict[str, Any]]
    purpose: str | None = None  # 건명. 없으면 자동 생성
    account: str | None = None  # 직원이 적은 계정과목 (M-05)
    verify_result: dict[str, Any] | None = None  # 이미 받은 /api/verify 응답. 없으면 서버가 다시 검증

    @field_validator("items")
    @classmethod
    def _not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("items가 비어 있습니다.")
        return v


class SubmissionView(BaseModel):
    """목록·상세 공통. 프론트 목업 한 건과 같은 키."""

    model_config = ConfigDict(extra="allow")

    id: str
    submitter: str
    dept: str
    type: str
    purpose: str
    merchant: str | None = None
    date: str | None = None
    time: str | None = None
    amount: int
    account: str | None = None
    submitted_at: str | None = None
    submitted_time: str | None = None  # 2026-11-13T15:02+09:00
    step: int | None = None
    verdict: str | None = None
    status: str
    items: list[dict[str, Any]] = []
    decision_message: str | None = None
    decided_at: str | None = None


class SubmissionList(BaseModel):
    total: int
    items: list[SubmissionView]


class DecisionRequest(BaseModel):
    decision: str  # 승인 / 반려
    message: str = ""


class RejectDraftRequest(BaseModel):
    issue_fields: list[str] = []
    # AI 판정 밖의 추가 사유 (예: M-05 계정과목 불일치). items[] 한 개와 같은 모양
    extra_issues: list[dict[str, Any]] = []


class RejectDraftResponse(BaseModel):
    message: str
    sources: list[str] = []
