"""U-04 청구 검증 요청·응답 모양 (docs/API.md 3-2).

검증 엔진(backend/app/precheck)은 API.md 필드 외에 선택 필드(trip, nights, time, payment …)를
더 받습니다. 그래서 요청은 정해진 필드 밖의 값도 그대로 통과시킵니다 (extra="allow").
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.constants import Verdict


class VerifyRequest(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "trip_type": "국내출장",
                    "grade": "직원 3급 이하",
                    "items": [
                        {
                            "field": "식비",
                            "amount": 27000,
                            "date": "2026-10-20",
                            "note": "조식 포함 숙박",
                        },
                        {"field": "숙박비", "amount": 80000, "date": "2026-10-20", "note": ""},
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


class VerifyItem(BaseModel):
    model_config = ConfigDict(extra="allow")  # 엔진이 붙이는 rule_id 등은 그대로 통과

    field: str
    verdict: Verdict
    message: str
    basis: str
    fix: str = ""


class VerifyResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    overall: Verdict
    items: list[VerifyItem]
