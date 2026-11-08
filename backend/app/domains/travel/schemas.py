"""U-05 출장비 계산 요청·응답 모양 (docs/API.md 3-5, docs/U-05_출장비계산.md).

계산 엔진(app/precheck/travel_calc.py)은 trip·fares·private_car 안의 선택 필드를 많이 받습니다.
그래서 요청·응답 모두 정해진 필드 밖의 값도 그대로 통과시킵니다 (extra="allow").
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class TravelCalcRequest(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "grade": "직원 3급 이하",
                    "trip": {
                        "start_date": "2026-10-20",
                        "end_date": "2026-10-21",
                        "region": "부산",
                        "vehicle": "자가용",
                        "private_car_approved": True,
                    },
                    "private_car": {
                        "distance_km": 200,
                        "fuel": "휘발유",
                        "price_per_liter": 1700,
                        "tolls": 0,
                        "public_fare": 59800,
                    },
                }
            ]
        },
    )

    trip_type: str = "국내출장"
    grade: str = "직원 3급 이하"
    trip: dict[str, Any] = {}


class TravelLine(BaseModel):
    model_config = ConfigDict(extra="allow")

    field: str
    amount: int | None
    type: str
    formula: str
    basis: str
    note: str = ""


class TravelCalcResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    grade: str
    lines: list[TravelLine]
    summary: dict[str, int]
    notes: list[str] = []
    verify_request: dict[str, Any]
