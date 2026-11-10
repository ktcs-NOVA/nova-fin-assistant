"""U-06 영수증 인식 요청/응답. 프론트 frontend/src/api/client.js recognizeReceipt() 와 같은 모양."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# 용도 후보는 이 목록 안에서만 (frontend client.js PURPOSES 와 같게 유지)
PURPOSES = ["식비", "회의비", "교통비", "숙박비", "주유비", "소모품비", "도서비", "경조사비", "기타"]


class ReceiptRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"filename": "receipt.jpg", "media_type": "image/jpeg", "image_base64": "/9j/4AAQ..."}]
        }
    )

    filename: str = "receipt"
    media_type: str = Field(description="image/jpeg · image/png · image/webp")
    image_base64: str = Field(description="사진 파일을 base64 로 인코딩한 문자열 (data: 접두사 없이)")


class ReceiptItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    amount: int | None = None


class ReceiptResponse(BaseModel):
    """사진에 없는 값은 null. 프론트는 이 값을 폼에 채우고 저장 전에 사람이 고칩니다."""

    model_config = ConfigDict(extra="allow")  # _meta 등 부가 정보 통과

    merchant: str | None = None
    business_type: str | None = None
    date: str | None = None
    time: str | None = None
    total_amount: int | None = None
    card_last4: str | None = None
    approval_no: str | None = None
    items: list[ReceiptItem] = []
    purpose_candidates: list[str] = []
    confidence: Literal["high", "medium", "low"] = "medium"
    notes: str | None = None
