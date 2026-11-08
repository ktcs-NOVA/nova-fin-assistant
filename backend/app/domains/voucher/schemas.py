"""U-07 결의서 초안 요청·응답 모양 (docs/API.md 3-6, docs/U-07_결의서초안.md).

요청은 U-04 /api/verify 와 같은 청구 내역입니다. 이미 받은 검증 결과가 있으면
verify_result 로 넘기면 검증을 다시 돌리지 않습니다.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class VoucherDraftRequest(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "trip_type": "국내출장",
                    "grade": "직원 3급 이하",
                    "trip": {
                        "start_date": "2026-10-20",
                        "end_date": "2026-10-21",
                        "region": "부산",
                    },
                    "requester": {"name": "노은비", "department": "재무팀"},
                    "items": [
                        {"field": "숙박비", "amount": 90000, "nights": 1},
                        {"field": "철도운임", "amount": 59800, "seat_class": "일반"},
                    ],
                }
            ]
        },
    )

    trip_type: str = "국내출장"
    grade: str = "직원 3급 이하"
    items: list[dict[str, Any]]

    @field_validator("items")
    @classmethod
    def _not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("items가 비어 있습니다.")
        return v


class VoucherDraftResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    document: str
    status: str
    header: dict[str, Any]
    summary: str
    lines: list[dict[str, Any]]
    attachments: list[dict[str, Any]]
    warnings: list[str] = []
