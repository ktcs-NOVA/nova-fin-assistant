# precheck — U-04 지출 사전검증 엔진

`POST /api/verify` 의 판정 로직입니다. 외부 라이브러리 없이 파이썬 표준 라이브러리만 씁니다.
규칙 목록과 근거 조항은 [docs/U-04_검증규칙표.md](../../docs/U-04_검증규칙표.md) 에 있습니다.

## 백엔드에서 쓰는 법

```python
from precheck import verify_claim

@app.post("/api/verify")
def verify(req: dict):
    try:
        return verify_claim(req)
    except ValueError as e:
        raise HTTPException(400, detail={"error": str(e)})
```

응답 형태는 `docs/API.md` 3-2와 같습니다 (`overall`, `items[].field/verdict/message/basis/fix`).
`items[].rule_id` 가 추가로 붙는데, 프론트는 무시해도 되고 테스트·관리자 화면에서 쓸 수 있습니다.

## 입력

API.md 요청 형태 그대로 동작합니다. 아래 **선택 필드**를 보내면 더 많은 규칙을 검사합니다.
없으면 해당 규칙을 건너뛰거나 "담당자 확인 필요"로 안내합니다.

```jsonc
{
  "trip_type": "국내출장",          // "국내출장" | "근무지 내 출장" | "법인카드" | "업무추진비"
  "grade": "직원 3급 이하",         // 사장 / 감사 / 임원·본부장 / 직원 1·2급 / 직원 3급 이하
  "trip": {                        // 선택: 출장 정보
    "start_date": "2026-10-20",
    "end_date": "2026-10-21",
    "region": "광역시",             // 서울 / 광역시 / 기타 (도시명도 가능: 부산, 세종, 제주 …)
    "vehicle": "대중교통",          // 대중교통 / 업무용차량 / 렌트차량 / 자가용
    "private_car_approved": false,
    "settlement_date": "2026-11-02",
    "hours": 3,                     // 근무지 내 출장만
    "round_trip_km": 12             // 근무지 내 출장만
  },
  "items": [
    {
      "field": "숙박비", "amount": 88000, "date": "2026-10-20", "note": "",
      // 선택 필드
      "nights": 1, "breakfast_included": true, "receipt": true,
      "seat_class": "일반", "passenger": false, "public_fare": 47000,
      "payment": "법인카드", "time": "23:30", "merchant": "OO식당", "merchant_type": "한식",
      "reason_doc": false,          // 별지 제5호 사유서 첨부 여부
      "pre_approved": false, "daily_audit": false,
      "attendees": ["해양수산부 OOO 과장"]
    }
  ]
}
```

- `note` 에 "조식", "특실", "동승", "사유서" 같은 단어가 있으면 해당 선택 필드가 있는 것으로 봅니다.
- 항목 유형은 `field` 이름으로 자동 분류합니다 (숙박 / 식비 / 일비 / 교통 / 업무추진비 / 조직관리비 / 경조).

## 테스트

```bash
cd backend
python -m unittest discover -s precheck/tests -t . -v
```

## 규정이 바뀌면

숫자와 업종 목록은 `rules.py` 한 곳에만 있습니다. 판정 로직(`engine.py`)은 건드리지 않아도 됩니다.
