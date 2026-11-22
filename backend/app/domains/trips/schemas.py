"""출장 신청 요청·응답 모양 (docs/API.md 3-15)."""

from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator

TripType = Literal["국내출장", "근무지 내 출장"]
Region = Literal["서울", "광역시", "기타"]
Vehicle = Literal["대중교통", "업무용차량", "렌트차량", "자가용"]


class Companion(BaseModel):
    """함께 가는 출장자 (신청인 본인 제외)."""

    name: str = Field(min_length=1, max_length=50)
    dept: str = Field("", max_length=50)


class TripCreate(BaseModel):
    trip_type: TripType = "국내출장"
    purpose: str = Field(min_length=1, max_length=200, examples=["부산 선사 방문 (선박금융 상담)"])
    destination: str | None = Field(None, max_length=100, examples=["부산 강서구 부산항 신항"])
    # 비우면 출장지 주소로 정합니다 (서울 · ○○광역시 → 광역시 · 나머지 → 기타)
    region: Region | None = None
    start_date: date
    end_date: date
    vehicle: Vehicle = "대중교통"
    private_car_approved: bool = False
    distance_km: float | None = Field(None, ge=0, description="사무실 → 출장지 편도 거리(km)")
    education: bool = False  # 근무지 외 교육 참석 (일비 2일 한도)
    hours: float | None = Field(None, ge=0, le=24, description="근무지 내 출장의 예상 출장 시간")
    start_time: time | None = Field(None, description="출발 시각 (선택)")
    end_time: time | None = Field(None, description="복귀 시각 (선택)")
    # 출장원 서식의 출장자 명단은 5줄 → 신청인 빼고 4명까지
    companions: list[Companion] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def _period(self) -> "TripCreate":
        if self.end_date < self.start_date:
            raise ValueError("출장 종료일이 시작일보다 앞설 수 없습니다.")
        if (
            self.start_date == self.end_date
            and self.start_time
            and self.end_time
            and self.end_time <= self.start_time
        ):
            raise ValueError("당일 출장은 복귀 시각이 출발 시각보다 늦어야 합니다.")
        return self


class TripSubmission(BaseModel):
    id: str  # 정산 번호 S-2026-001
    status: str  # 검토 대기 / 승인 / 반려
    verdict: str | None = None


class TripView(BaseModel):
    id: int
    trip_type: str
    purpose: str
    destination: str | None
    region: str | None
    start_date: date
    end_date: date
    vehicle: str | None
    private_car_approved: bool
    distance_km: float | None
    education: bool
    hours: float | None
    start_time: time | None
    end_time: time | None
    companions: list[Companion]
    status: str  # 신청 / 취소
    # 화면에 보일 진행 단계: 출장 예정 / 출장 중 / 정산 전 / 정산 제출 / 취소
    stage: str
    submission: TripSubmission | None = None  # 이 출장으로 낸 가장 최근 정산
