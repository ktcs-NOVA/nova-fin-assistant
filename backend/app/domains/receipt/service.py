"""U-06 영수증 인식: 사진 1장 → 가맹점·금액·일시·용도 후보.

experiments/receipt-ocr/extract_receipts.py 의 지시문과 출력 형식을 그대로 가져와
팀 공용 OpenAI 키(app/ai/llm.py)로 읽습니다. 키가 없으면 예시 값을 돌려줍니다.
"""

import base64
import logging
import re
import time

from app.ai import llm
from app.ai.masking import mask
from app.core.config import settings
from app.core.errors import AppError
from app.domains.receipt.schemas import PURPOSES, ReceiptRequest, ReceiptResponse

log = logging.getLogger("nova.receipt")

ALLOWED_MEDIA = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 10 * 1024 * 1024

SYSTEM = f"""당신은 한국 영수증(카드 매출전표 또는 간이 영수증) 판독기입니다.
사진에서 값을 읽어 JSON 객체 하나로만 답하세요. 아래 설명문을 값으로 베끼지 말고, 사진에 없는 값은 지어내지 말고 null 로 두세요.

키와 뜻
- merchant: 가맹점(상호)명 (문자열)
- business_type: 업종 추정. 예: 음식점, 카페, 편의점, 주유소, 숙박, 택시, 서점 (문자열)
- date: 결제 날짜 YYYY-MM-DD (문자열)
- time: 결제 시각 HH:MM, 24시간 (문자열)
- total_amount: 최종 결제(합계) 금액, 원 단위 정수 (숫자)
- card_number: 카드번호를 영수증에 적힌 그대로, 별표(*)와 구분자까지 포함 (문자열). 가려진 자리를 추측하지 마세요
- approval_no: 승인번호 (문자열)
- items: 품목 목록 [{{"name": 품목명 그대로, "amount": 품목 금액 정수 또는 null}}]. 없으면 []
- purpose_candidates: 이 지출의 용도 후보, 가능성 높은 순 1~3개. 다음 중에서만: {", ".join(PURPOSES)}
- confidence: 전체 판독 신뢰도 "high" | "medium" | "low"
- notes: 흐림·잘림·추정한 부분 등 사람이 확인해야 할 메모 (문자열). 없으면 null

규칙
- 날짜는 YYYY-MM-DD, 시각은 24시간 HH:MM 으로 통일합니다. (예: 2026.10.20 / 26-10-20 → 2026-10-20, 오후 7:35 → 19:35)
- 금액은 쉼표와 '원'을 빼고 정수로 적습니다. 합계는 최종 결제 금액(할인·포인트 적용 후)입니다.
- 숫자 0 과 영문 O, 1 과 l 처럼 헷갈리는 부분, 흐려서 추정한 부분은 notes 에 적어 주세요.
- notes 에는 카드번호·승인번호·전화번호·사업자번호·가맹점번호·사람 이름을 적지 마세요. "카드번호가 가려져 있음" 처럼 사실만 적습니다.

답 형식 (키 이름은 이대로):
{{"merchant": null, "business_type": null, "date": null, "time": null, "total_amount": null, "card_number": null,
  "approval_no": null, "items": [], "purpose_candidates": [], "confidence": "medium", "notes": null}}
"""

# 키가 없을 때 화면 흐름을 확인할 수 있게 돌려주는 예시 값 (가상)
MOCK_RESULT = {
    "merchant": "(예시) OO카페",
    "business_type": "카페",
    "date": "2026-11-03",
    "time": "14:31",
    "total_amount": 6000,
    "card_last4": None,
    "approval_no": "****0000",
    "items": [{"name": "아메리카노", "amount": 6000}],
    "purpose_candidates": ["식비", "회의비"],
    "confidence": "low",
    "notes": "[목업 AI] OPENAI_API_KEY 가 없어 실제 인식 대신 예시 값을 돌려줍니다.",
}


def _decode_image(req: ReceiptRequest) -> bytes:
    if req.media_type not in ALLOWED_MEDIA:
        raise AppError(f"지원하지 않는 사진 형식입니다: {req.media_type}. jpg/png/webp 만 됩니다.")
    raw = req.image_base64.strip()
    if raw.startswith("data:"):  # data:image/png;base64,.... 로 오면 접두사 제거
        raw = raw.split(",", 1)[-1]
    try:
        image = base64.standard_b64decode(raw)
    except (ValueError, TypeError):
        raise AppError("image_base64 를 해독할 수 없습니다.")
    if not image:
        raise AppError("사진 데이터가 비어 있습니다.")
    if len(image) > MAX_BYTES:
        raise AppError("사진이 10MB 를 넘습니다. 줄여서 다시 올려 주세요.")
    return image


def _mask_tail(value, keep: int = 4) -> str | None:
    """승인번호처럼 식별용 번호는 뒷자리만 남깁니다 ("30004889" → "****4889"). 숫자가 없으면 None."""
    if value is None:
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    if not digits:
        return None
    return "****" + digits[-keep:]


def _clean(data: dict) -> dict:
    """모델 출력을 응답 형식에 맞게 다듬습니다 (용도 후보는 목록 안의 값만, 금액은 정수, 개인정보는 가림)."""
    out = dict(data)
    cands = [p for p in (out.get("purpose_candidates") or []) if p in PURPOSES]
    out["purpose_candidates"] = list(dict.fromkeys(cands))[:3] or ["기타"]
    if out.get("confidence") not in ("high", "medium", "low"):
        out["confidence"] = "medium"
    if isinstance(out.get("total_amount"), str):
        digits = re.sub(r"[^\d]", "", out["total_amount"])
        out["total_amount"] = int(digits) if digits else None
    items = []
    for it in out.get("items") or []:
        if not isinstance(it, dict):
            continue
        amt = it.get("amount")
        if isinstance(amt, str):
            digits = re.sub(r"[^\d]", "", amt)
            amt = int(digits) if digits else None
        items.append({"name": str(it.get("name") or ""), "amount": amt})
    out["items"] = items
    # 카드 뒷 4자리: 모델에게는 적힌 그대로(card_number)를 받고 여기서 뒷자리를 정합니다.
    # 별표 뒤에 남은 숫자만 뒷자리로 인정 ("**** 1234" → 1234, "5239-3000-****-****" → 모름)
    # 카드번호처럼 보이지 않는 짧은 값(승인번호 조각 등)은 버립니다: 숫자·별표가 8자 이상이어야 함
    raw = out.pop("card_number", None) or out.get("card_last4")
    out["card_last4"] = None
    if raw is not None:
        raw = str(raw)
        if len(re.sub(r"[^\d*]", "", raw)) >= 8:
            tail = raw.rsplit("*", 1)[-1] if "*" in raw else raw
            digits = re.sub(r"[^\d]", "", tail)
            out["card_last4"] = digits[-4:] if len(digits) >= 4 else None
    # 승인번호는 뒷 4자리만, 메모 문장에 섞인 카드·전화·사업자번호는 가립니다 (PM 요청 2026-11-10)
    out["approval_no"] = _mask_tail(out.get("approval_no"))
    if out.get("notes"):
        out["notes"] = mask(str(out["notes"]))
    return out


def recognize(req: ReceiptRequest) -> dict:
    image = _decode_image(req)
    if settings.ai_mock:
        return {**MOCK_RESULT, "_meta": {"model": "mock", "bytes": len(image)}}

    t0 = time.time()
    try:
        data = llm.read_image_json(SYSTEM, base64.standard_b64encode(image).decode("ascii"), req.media_type,
                                   model=settings.receipt_model)
    except Exception as e:  # openai 예외 종류별 안내
        name = type(e).__name__
        log.warning("receipt %s 인식 실패: %s", req.filename, e)
        if name == "AuthenticationError":
            raise AppError("OpenAI API 키가 없거나 잘못되었습니다. backend/.env 를 확인해 주세요.", 500)
        if name == "RateLimitError":
            raise AppError("API 호출이 너무 잦습니다. 잠시 후 다시 시도해 주세요.", 429)
        raise AppError(f"영수증 인식 API 오류: {e}", 502)

    elapsed = round(time.time() - t0, 1)
    if not data:
        raise AppError("영수증을 읽지 못했습니다. 사진을 더 밝고 선명하게 찍어 다시 올려 주세요.", 502)
    result = ReceiptResponse.model_validate(_clean(data)).model_dump()
    result["_meta"] = {"model": settings.receipt_model, "seconds": elapsed, "bytes": len(image)}
    log.info("receipt %s (%d KB) → %s / %s원 / %s (%.1fs)", req.filename, len(image) // 1024,
             result.get("merchant"), result.get("total_amount"), result.get("confidence"), elapsed)
    return result
