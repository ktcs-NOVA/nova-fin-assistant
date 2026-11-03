"""체크리스트 (U-02 업무절차 안내와 연결 예정).

지금은 고정된 예시 응답(frontend/src/mocks/checklist.json 과 같은 모양)을 돌려줍니다.
TODO: 경비 종류별 체크 항목을 규정(RAG) + 규칙으로 만들기.
"""

SAMPLE_ITEMS = [
    {
        "id": 1,
        "text": "(예시) 출장 종료 후 15일 이내에 정산했나요?",
        "basis": "여비규정 제3조의2 제2항",
    },
    {"id": 2, "text": "(예시) 숙박비·교통비 영수증을 첨부했나요?", "basis": "여비규정 제10조"},
    {
        "id": 3,
        "text": "(예시) 숙박에 조식이 포함되어 있다면 식비를 1/3 차감했나요?",
        "basis": "여비규정 제11조 제4항",
    },
]


def get_checklist(expense_type: str) -> dict:
    return {"type": expense_type, "items": [dict(x) for x in SAMPLE_ITEMS]}
