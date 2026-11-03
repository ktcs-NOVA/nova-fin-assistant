"""U-04 청구 검증.

판정 로직은 규칙 엔진(app/precheck)을 그대로 씁니다.
엔진이 아직 합쳐지지 않았으면 예시 응답(frontend/src/mocks/verify.json 과 같은 모양)을 돌려줍니다.
"""

import copy
import logging

from app.core.errors import AppError

log = logging.getLogger("nova.verify")

try:
    from app.precheck import verify_claim as _engine  # 합친 뒤 위치
except ImportError:
    try:
        from precheck import verify_claim as _engine  # 합치기 전 위치 (backend/precheck)
    except ImportError:
        _engine = None

SAMPLE = {
    "overall": "보완 필요",
    "items": [
        {
            "field": "식비",
            "verdict": "보완 필요",
            "message": "(예시) 숙박비에 조식이 포함되어 있어 식비의 1/3을 차감해야 합니다.",
            "basis": "여비규정 제11조 제4항",
            "fix": "식비 청구액을 27,000원에서 18,000원으로 수정",
        },
        {
            "field": "숙박비",
            "verdict": "규정상 확인 가능",
            "message": "(예시) 기타 지역 숙박비 상한(80,000원) 이내입니다.",
            "basis": "여비규정 별표 1",
            "fix": "",
        },
        {
            "field": "교통비(자가용)",
            "verdict": "담당자 확인 필요",
            "message": "(예시) 자가용 이용은 사전 승인이 필요합니다. 승인 여부를 확인해 주세요.",
            "basis": "여비규정 제13조 제5항",
            "fix": "출장 신청서의 자가용 승인 여부 확인 후 첨부",
        },
    ],
}


def engine_available() -> bool:
    return _engine is not None


def verify(claim: dict) -> dict:
    if _engine is None:
        return copy.deepcopy(SAMPLE)
    try:
        return _engine(claim)
    except ValueError as e:  # 엔진이 입력 오류를 ValueError 로 알려줌
        raise AppError(str(e), 400) from e
