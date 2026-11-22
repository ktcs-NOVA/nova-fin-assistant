# 프론트엔드 · 백엔드 베이스코드 연동 조율 문서

> 작성: 프론트엔드/UI 담당 · 2026-10-29
> 받는 사람: 백엔드 베이스코드 담당
> 목적: 10/28 회의에서 "프론트 베이스코드 + 백엔드 베이스코드를 각각 만들고 합친다"로 정했는데, 합칠 때 안 꼬이게 **미리 맞춰둘 것**을 정리했습니다. 저희 둘 다 전문가가 아니라서 최대한 쉽게 썼습니다. 모르는 부분은 그냥 물어봐 주세요.

---

## 0. 한 장 요약

합친다는 건 결국 **"프론트가 어떤 주소로 무엇을 보내고, 백엔드가 무엇을 돌려주는지"** 를 맞추는 일입니다. 아래 5가지만 맞추면 서로 기다리지 않고 각자 만들 수 있습니다.

| 번호 | 맞출 것 | 누가 하나 | 상태 |
|---|---|---|---|
| 1 | 백엔드 실행 방법·주소 알려주기 | 백엔드 | ☐ |
| 2 | CORS 허용 설정 | 백엔드 | ☐ |
| 3 | API 주소 3개와 주고받는 데이터 모양 합의 | 둘이 함께 | ☐ |
| 4 | 에러일 때 돌려주는 모양 합의 | 둘이 함께 | ☐ |
| 5 | 서로 기다리지 않는 작업 규칙 | 둘이 함께 | ☐ |

---

## 1. 백엔드 실행 방법·주소 (백엔드가 알려줄 것)

프론트를 만들다 보면 제 노트북에서 백엔드를 같이 켜서 테스트해야 합니다. 그래서 아래 4가지를 알려주시면 됩니다.

| 질문 | 예시 답 | 실제 답 (채워주세요) |
|---|---|---|
| 어떤 프레임워크인가요? | FastAPI | |
| 어떤 포트로 뜨나요? | http://localhost:8000 | |
| 실행 명령어는? | `uvicorn main:app --reload` | |
| 주소 앞에 공통으로 붙는 게 있나요? | 전부 `/api/`로 시작 | |

> 왜 필요한가요?
> 프론트는 "백엔드 주소"를 설정 파일 한 곳에 적어두고 모든 요청을 그 주소로 보냅니다. 이것만 알면 프론트 쪽 설정은 끝입니다.

---

## 2. CORS 허용 설정 (백엔드가 해줄 것)

**요청 한 줄:** 개발 중에는 `http://localhost:5173` 에서 오는 요청을 허용해 주세요.

> CORS가 뭔가요?
> 브라우저는 안전을 위해 "다른 포트에서 뜬 서버"로 보내는 요청을 기본적으로 막습니다.
> 프론트는 5173번, 백엔드는 8000번으로 뜨면 서로 다른 포트라서 막힙니다.
> 그래서 백엔드 쪽에서 "5173에서 오는 건 허용해"라고 한 번 설정해야 합니다.
> 이걸 안 하면 프론트에서 요청을 보낼 때 빨간 에러만 뜨고 아무 일도 안 일어납니다. 가장 자주 막히는 지점이라 미리 부탁드립니다.

FastAPI라면 아래 다섯 줄입니다.

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 3. API 주소 3개와 데이터 모양 (가장 중요, 함께 정할 것)

"API 주소"는 기능마다 붙는 주소라고 생각하시면 됩니다. 저희 기능이 3개니까 주소도 3개입니다. 아래는 제안이고, 바꾸고 싶은 부분은 말씀해 주세요.

| 기능 | 방식 | 주소 | 프론트가 보내는 것 | 백엔드가 돌려주는 것 |
|---|---|---|---|---|
| 규정 Q&A | POST | `/api/qa` | 질문 문장 | 답변 문장 + 근거 조항 |
| 청구 검증 | POST | `/api/verify` | 청구 내역 (항목별 금액·날짜 등) | 항목별 판정 + 근거 조항 + 수정 방법 |
| 체크리스트 | GET | `/api/checklist` | 없음 (또는 경비 종류) | 체크 항목 목록 |
| 업무절차 안내 (U-02) | POST | `/api/procedure` | 알고 싶은 업무 | 필요 서류 · 작성 순서 · 기한 · 결재자 + 근거 조항 |

### 3-1. 규정 Q&A (`POST /api/qa`)

프론트가 보내는 것:
```json
{ "question": "출장 때 자가용 쓰면 비용 어떻게 돼요?" }
```

백엔드가 돌려주는 것:
```json
{
  "answer": "자가용 이용은 사전 승인이 필요하며[1], 승인 시 철도·자동차 운임 범위 안에서 지급됩니다[2].",
  "grounded": true,
  "sources": [
    { "ref": 1, "regulation": "여비규정", "article": "제13조 제5항", "revised_at": "2025-09-23", "url": null },
    { "ref": 2, "regulation": "여비규정", "article": "제13조 제6항", "revised_at": "2025-09-23", "url": null }
  ]
}
```

> **2026-11-06 추가 (U-03 근거·출처 표시)** — 기존 필드는 그대로이고 아래 필드만 늘었습니다.
>
> | 필드 | 뜻 |
> |---|---|
> | `grounded` | `false` 면 규정에서 근거를 못 찾은 답변. 화면에 "담당자 확인 필요"를 표시하고 `sources` 는 빈 배열 |
> | `sources[].ref` | 답변 본문의 `[1]`, `[2]` 인용 번호와 짝. 1부터 차례대로 |
> | `sources[].revised_at` | 조항 최근 개정일 (`YYYY-MM-DD`, 없으면 `null`) |
> | `sources[].url` | 원문 링크 (없으면 `null`) |
>
> **2026-11-08 추가 (챗봇 도구 선택)** — 백엔드가 질문을 보고 답하는 방식을 고릅니다. 기존 필드는 그대로입니다.
>
> | 필드 | 뜻 |
> |---|---|
> | `type` | `answer` 규정 답변 / `procedure` 절차 안내 / `clarify` 어떤 업무인지 되묻기 |
> | `procedure` | `type` 이 `procedure` 일 때 3-4 응답과 같은 모양. `answer` 에는 요약이 들어감 |
> | `options` | `type` 이 `clarify` 일 때 고를 수 있는 업무 이름 목록 |
> | `contact` | `grounded` 가 `false` 일 때 안내할 담당자 `{ department, name, phone }`. 지금은 시연용 가상 계정이고, 계정이 없으면 `null` |
>
> 도구 선택 정확도는 `uv run python -m scripts.eval_route` 로 확인합니다 (`data/eval/route_eval.csv`).
>
> **2026-11-18 추가 (U-03 근거 미리보기)** — 규정 Q&A 의 `sources[]` 에만 채워지고, 다른 기능의 `sources` 는 `null` 입니다.
>
> | 필드 | 뜻 |
> |---|---|
> | `sources[].chunk_type` | `article` 조문 / `table` 별표. `table` 이면 화면에서 표로 그림 |
> | `sources[].excerpt` | 조항 본문. 별표는 한 행이 `구분: 직원(3급 이하) \| 식비(1일당): 27 \| …` 한 줄. 인용 번호·근거 조항에 마우스를 올리면(휴대폰은 탭) 보여 줌 |
>
> 조항이 "별표 1에 따라"처럼 표를 가리키면 백엔드가 그 별표를 근거에 함께 넣어, 답변이 "별표를 확인하세요" 대신 숫자로 답합니다.

### 3-2. 청구 검증 (`POST /api/verify`) ★ 모양을 꼭 고정해야 하는 부분

프론트가 보내는 것:
```json
{
  "trip_type": "국내출장",
  "grade": "직원 3급 이하",
  "items": [
    { "field": "식비", "amount": 27000, "date": "2026-10-20", "note": "조식 포함 숙박" },
    { "field": "숙박비", "amount": 80000, "date": "2026-10-20", "note": "" }
  ]
}
```

백엔드가 돌려주는 것:
```json
{
  "overall": "보완 필요",
  "items": [
    {
      "field": "식비",
      "verdict": "보완 필요",
      "message": "숙박비에 조식이 포함되어 있어 식비의 1/3을 차감해야 합니다.",
      "basis": "여비규정 제11조 제4항",
      "fix": "식비 청구액을 27,000원에서 18,000원으로 수정"
    },
    {
      "field": "숙박비",
      "verdict": "규정상 확인 가능",
      "message": "기타 지역 숙박비 상한(80,000원) 이내입니다.",
      "basis": "여비규정 별표 1",
      "fix": ""
    }
  ]
}
```

**꼭 지켜주셨으면 하는 것 한 가지**

`verdict` 와 `overall` 값은 아래 **세 가지 문자열로만** 보내주세요. 프론트에서 이 글자를 보고 색을 정합니다.

| 값 | 의미 | 프론트 표시 |
|---|---|---|
| `규정상 확인 가능` | 문제 없음 | 초록 |
| `보완 필요` | 규정에 어긋나니 고쳐야 함 | 빨강 |
| `담당자 확인 필요` | 규정만으로 판단 불가, 사람이 봐야 함 | 노랑 |

> 왜 모양을 고정하나요?
> 프론트의 "검증 결과 카드"는 이 모양을 보고 그려집니다.
> 필드 이름이 하나라도 바뀌면 (예: `basis` → `reason`) 카드가 깨집니다.
> 그래서 처음에 한 번 정하고, 바꿀 일이 생기면 **바꾸기 전에** 알려주시면 됩니다.

### 3-3. 체크리스트 (`GET /api/checklist?type=국내출장`)

백엔드가 돌려주는 것:
```json
{
  "type": "국내출장",
  "items": [
    { "id": 1, "text": "출장 종료 후 15일 이내에 정산했나요?", "basis": "여비규정 제3조의2 제2항" },
    { "id": 2, "text": "숙박비 영수증을 첨부했나요?", "basis": "여비규정 제10조" },
    { "id": 3, "text": "숙박에 조식이 포함되어 있다면 식비를 1/3 차감했나요?", "basis": "여비규정 제11조 제4항" }
  ]
}
```

### 3-4. 업무절차 안내 (`POST /api/procedure`) — U-02

> 2026-11-08 변경. 서류·순서·기한은 업무별로 조항과 함께 정해 둔 내용을 안내하고, 결재자는 위임전결규정 시행세칙 별표에서 조회합니다. 근거 표현이 현재 규정에 없으면 `grounded: false` 로 답합니다.
> 안내하는 업무는 국내·국외 출장비 정산, 법인카드 사용 후 처리, 업무추진비 집행입니다. 그 밖의 업무는 `grounded: false` 로 답합니다. 응답 모양은 그대로입니다.

프론트가 보내는 것:
```json
{ "task": "국내 출장비 정산하려면?" }
```

백엔드가 돌려주는 것:
```json
{
  "task": "국내 출장비 정산",
  "summary": "출장보고서와 정산 출장원을 작성하고 증빙을 붙여 15일 안에 정산을 신청합니다.",
  "documents": [
    { "name": "출장원(정산)", "detail": "별지 제3호 서식", "basis": "여비규정 별지 제3호 서식" }
  ],
  "steps": [
    { "title": "출장결과보고 승인", "detail": "출장승인권자가 금액과 증빙을 확인", "basis": "여비규정 제3조의2 제3항" }
  ],
  "deadline": { "text": "출장을 마친 날부터 15일 이내", "basis": "여비규정 제3조의2 제2항" },
  "approver": { "text": "「위임전결규정 시행세칙」에서 정한 전결권자", "basis": "여비규정 제3조의2 제1항", "check": true },
  "grounded": true,
  "sources": [
    { "ref": 1, "regulation": "여비규정", "article": "제3조의2", "revised_at": "2026-10-21", "url": null }
  ]
}
```

- `documents` ① 필요 서류, `steps` ② 작성 순서, `deadline` ③ 제출 기한, `approver` ④ 결재자
- `check: true` 는 규정만으로 확정할 수 없어 "담당자 확인 필요"로 표시할 항목
- `sources` 모양은 3-1 과 같습니다.

### 3-5. 출장비 계산 (`POST /api/travel-calc`) — U-05

> 2026-11-08 추가. 입력·출력 전체와 계산 규칙은 [U-05_출장비계산.md](U-05_출장비계산.md) 참고.

프론트가 보내는 것 (자가용 예시):
```json
{
  "grade": "직원 3급 이하",
  "trip": { "start_date": "2026-10-20", "end_date": "2026-10-20", "vehicle": "자가용" },
  "private_car": { "distance_km": 200, "fuel": "휘발유", "price_per_liter": 1700, "tolls": 0, "public_fare": 100000 }
}
```

백엔드가 돌려주는 것 (요약):
```json
{
  "grade": "직원 3급 이하",
  "lines": [
    { "field": "일비", "amount": 30000, "type": "정액", "formula": "30,000원 × 1일", "…": "…" },
    { "field": "식비", "amount": 27000, "type": "정액", "formula": "27,000원 × 1일", "…": "…" },
    { "field": "교통비(자가용)", "amount": 37778, "type": "실비(한도)",
      "formula": "200km ÷ 9.0km/L(휘발유) × 1,700원/L", "basis": "여비규정 제13조 제6항, 별표 1 주2)",
      "note": "유류비 산식은 실무자 의견 반영(멘토 제공 산식)입니다." }
  ],
  "summary": { "fixed_total": 57000, "lodging_cap": 0, "transport_total": 37778, "estimated_max": 94778 },
  "notes": ["자가용은 출장승인권자가 인정한 경우에만 가능합니다 (제13조 제5항)."],
  "verify_request": { "trip_type": "국내출장", "grade": "직원 3급 이하", "trip": {}, "items": [] }
}
```

- 화면은 `summary.estimated_max` 를 "받을 수 있는 금액"으로 크게 보여주고, `lines` 로 항목별 계산식을 보여주면 됩니다.
- `verify_request` 를 그대로 `/api/verify` 에 보내면 U-04 검증으로 이어집니다.

### 3-6. 결의서 초안 (`POST /api/voucher-draft`) — U-07

> 2026-11-08 추가. 자세한 규칙은 [U-07_결의서초안.md](U-07_결의서초안.md) 참고.

프론트가 보내는 것: `/api/verify` 와 같은 청구 내역 (+ 선택: `trip`, `requester`, `verify_result`)
```json
{
  "trip_type": "국내출장",
  "grade": "직원 3급 이하",
  "trip": { "start_date": "2026-10-20", "end_date": "2026-10-21", "region": "부산" },
  "items": [ { "field": "숙박비", "amount": 90000, "nights": 1 } ]
}
```

백엔드가 돌려주는 것: `document`, `status`("제출 가능" / "제출 전 보완 필요"), `header`(건명·작성일·합계 등),
`summary`(적요), `lines`(계정과목별 금액), `attachments`(첨부서류), `deadlines`, `verify`, `warnings`, `approval_note`.
`items` 가 비어 있으면 400 `{"error": "items가 비어 있습니다."}`.

### 3-7. 내 체크리스트 (`/api/checklists`) — U-02

> **2026-11-14: 화면에서 뺐습니다.** 11/13 코칭에서 체크리스트 기능을 제외하기로 해서 프론트는 이 API 를 더 부르지 않습니다 (저장 버튼·목록 탭 삭제). API 와 테이블은 그대로 남아 있습니다.

업무 절차 안내를 직원별로 저장하고 체크합니다. 3-3 의 `/api/checklist` 는 예시 응답이고 화면에서 쓰지 않습니다.

| 하는 일 | 방식 | 주소 | 프론트가 보내는 것 |
|---|---|---|---|
| 목록 조회 | GET | `/api/checklists` | 없음 |
| 저장 | POST | `/api/checklists` | `{ "task": "국내 출장비 정산" }` (3-4 응답의 `task`) |
| 체크 | PATCH | `/api/checklists/{id}/items/{itemId}` | `{ "done": true }` |
| 삭제 | DELETE | `/api/checklists/{id}` | 없음 (응답 본문 없음, 204) |

저장·조회가 돌려주는 것:
```json
{
  "id": 1,
  "task": "국내 출장비 정산",
  "summary": "출장원(정산)과 출장보고서에 증빙을 붙여 15일 이내에 정산합니다.",
  "deadline": { "text": "출장을 완료한 날부터 15일 이내", "basis": "여비규정 제3조의2 제2항", "check": false },
  "approver": { "text": "부서장을 제외한 직원: 부서장", "basis": "위임전결규정 시행세칙 별표", "check": false },
  "sources": [{ "ref": 1, "regulation": "여비규정", "article": "제3조의2", "revised_at": "2026-10-21", "url": null }],
  "created_at": "2026-11-08T09:00:00+09:00",
  "items": [
    { "id": 10, "kind": "document", "title": "출장보고서", "detail": "별지 제4호 서식.", "basis": "여비규정 별지 제4호 서식", "done": false, "done_at": null }
  ]
}
```

- `kind` 는 `document`(필요 서류) 또는 `step`(작성 순서)입니다.
- 사용자는 `Authorization: Bearer <token>` 헤더의 로그인 토큰으로 구분합니다 (3-10). 토큰이 없으면 401.
- 내용은 저장 시점의 복사본입니다. 규정이 개정되어도 저장한 내용은 바뀌지 않습니다.

---

### 3-8. 영수증 인식 (`POST /api/receipt`) — U-06, 2026-11-03 추가 · **2026-11-10 백엔드 구현 완료**

프론트의 "영수증 등록" 화면이 사진 1장을 보내면, 백엔드가 팀 공용 OpenAI 키(`gpt-4o-mini`, 이미지 입력)로 값을 읽어 돌려줍니다 (`app/domains/receipt/`). 키가 없으면 `notes` 에 `[목업 AI]` 가 붙은 예시 값을 돌려줍니다.
프론트는 사진을 base64 문자열로 보냅니다. (multipart 가 편하시면 말씀해 주세요. 프론트 쪽 한 줄만 바꾸면 됩니다.)

프론트가 보내는 것:
```json
{ "filename": "receipt.jpg", "media_type": "image/jpeg", "image_base64": "/9j/4AAQ..." }
```
`media_type` 은 `image/jpeg` · `image/png` · `image/webp` 중 하나입니다.

백엔드가 돌려주는 것 (사진에 없는 값은 `null`):
```json
{
  "merchant": "유로드밀 (Euro De Meal)",
  "business_type": "카페",
  "date": "2026-10-29",
  "time": "10:59",
  "total_amount": 20000,
  "card_last4": null,
  "approval_no": "****9793",
  "items": [
    { "name": "아메리카노Hot", "amount": 4000 },
    { "name": "감자크림스프", "amount": 5000 }
  ],
  "purpose_candidates": ["식비", "회의비"],
  "confidence": "high",
  "notes": "카드번호 뒷자리가 가려져 있어 card_last4 는 null."
}
```

| 필드 | 설명 |
|---|---|
| `date` / `time` | `YYYY-MM-DD` / 24시간 `HH:MM` |
| `total_amount` | 쉼표·원 없는 정수 (최종 결제 금액) |
| `card_last4` | 뒷 4자리만. 가려져 있으면 `null` (대부분의 영수증이 그렇습니다) |
| `approval_no` | 뒷 4자리만 `****4889` 형태로. 중복 청구 확인용이라 끝자리면 충분합니다 |
| `purpose_candidates` | `식비 회의비 교통비 숙박비 주유비 소모품비 도서비 경조사비 기타` 중 1~3개, 가능성 높은 순 |
| `confidence` | `high` / `medium` / `low`. 프론트는 `medium` 이하를 노란 배지로 표시합니다 |
| `notes` | 흐림·잘림·추정한 부분. 화면에 "AI 메모"로 그대로 보여줍니다. 카드·전화·사업자번호가 섞여 있으면 백엔드가 `[카드번호]` 식으로 가립니다 |

오류: 지원하지 않는 형식·빈 사진·10MB 초과는 400, API 키 문제는 500, 호출 제한은 429, 그 밖의 인식 실패는 502 (`{"error": ...}`).

정답률 (2026-11-10, 샘플 11장, `uv run python -m scripts.eval_receipt`): 날짜·합계 100%, 가맹점 82%, 시각 82~91%, 용도 후보 82%, 전체 89%. `gpt-4o-mini` 와 `gpt-4o` 가 같아서 기본은 mini 입니다 (`RECEIPT_MODEL` 로 변경). 지난 Claude 실험(100%)보다 낮으므로 화면의 "저장 전 직접 수정" 단계가 중요합니다. 가려진 카드번호는 모델 출력 대신 백엔드가 별표 뒤 숫자만 뒷자리로 인정합니다. 실험 서버(`experiments/receipt-ocr/server.py`)는 더 이상 켤 필요가 없습니다.

개인정보 (2026-11-10 PM 요청): 응답의 승인번호는 뒷 4자리만, 메모의 카드·전화·사업자번호는 가려서 내보냅니다(`app/ai/masking.py`). 화면의 샘플 사진 11장(`frontend/public/receipts/`)도 카드번호·승인번호·전화번호·대표자명·사업자번호를 검게 칠한 판본으로 바꿨습니다. 원본은 깃에 올라가지 않는 `experiments/receipt-ocr/receipts/` 에만 두고, 정답률 측정(`scripts.eval_receipt`)은 원본으로 합니다. 그래서 화면에서 샘플을 고르면 승인번호·카드 뒷자리는 비어 나오는 것이 정상입니다.

### 3-9. 정산 제출 · 검토 대기함 (`/api/submissions`, `/api/admin/submissions`) — M-01, 2026-11-09 추가

직원이 청구 검증(U-04)을 마친 내역을 제출하면 DB(`submissions`·`expenses`·`trips`)에 저장되고, 회계 관리자가 목록·상세에서 승인/반려합니다.
사용자는 `Authorization: Bearer <token>` 헤더의 로그인 토큰으로 구분합니다 (3-10). 관리자 주소는 `role=admin` 계정만 쓸 수 있고, 직원이 부르면 403.

| 하는 일 | 방식 | 주소 | 누가 | 프론트가 보내는 것 |
|---|---|---|---|---|
| 제출(검토 요청) | POST | `/api/submissions` | 직원 | `/api/verify` 요청과 같은 청구 내역 + `purpose`(건명), `account`(계정과목), `verify_result`(이미 받은 판정, 없으면 서버가 다시 검증) |
| 내 제출 내역 | GET | `/api/submissions` | 직원 | 없음 |
| 검토 대기함 목록 | GET | `/api/admin/submissions` | 관리자 | 없음 |
| 제출 건 상세 | GET | `/api/admin/submissions/{code}` | 관리자 | 없음 (`code` 는 `S-2026-003` 같은 번호) |
| 승인/반려 저장 | POST | `/api/admin/submissions/{code}/decision` | 관리자 | `{ "decision": "승인" \| "반려", "message": "반려 사유" }` (반려는 message 필수, 이미 처리된 건은 409) |
| 반려 메시지 초안 | POST | `/api/admin/submissions/{code}/reject-draft` | 관리자 | `{ "issue_fields": ["식비", ...], "extra_issues": [{ field, verdict, message, basis, fix }] }` |

제출·상세가 돌려주는 한 건 (목록은 `{ "total": N, "items": [...] }`). `frontend/src/mocks/submissions.json` 의 한 건과 같은 키:
```json
{
  "id": "S-2026-003", "submitter": "박철환", "dept": "총무인사부", "type": "국내출장",
  "purpose": "출장 여비 정산 (2026-10-20, 광역시)", "merchant": null, "date": "2026-10-20", "time": null,
  "amount": 271800, "account": "업무추진비", "submitted_at": "2026-11-09", "step": 5,
  "verdict": "보완 필요", "status": "검토 대기",
  "items": [ { "field": "식비", "verdict": "보완 필요", "message": "...", "basis": "여비규정 제11조 제4항", "fix": "..." } ],
  "expenses": [ { "field": "숙박비", "amount": 98000, "date": "2026-10-20", "payment": "여비 지급", "nights": 1, "breakfast_included": true } ],
  "decision_message": null, "decided_at": null
}
```

- `items` 는 제출 시점의 AI 판정(U-04 응답의 `items`)을 그대로 저장한 것. `expenses` 는 직원이 적은 지출 항목.
- `step` 은 상단 처리 단계: 제출되면 5(관리자 검토), 승인/반려되면 6.
- 반려 초안은 선택한 판정 항목의 메시지·근거·수정 방법으로 먼저 만들고, OpenAI 키가 있으면 LLM 이 안내문 형태로 다듬습니다. 근거 조항은 새로 만들지 않고 판정에 있던 것만 씁니다. 응답 `{ "message", "sources": ["여비규정 제11조 제4항", ...] }`.
- 판정 없이 들어온 건(시드 예시 등)은 조회할 때 지출 항목으로 검증을 한 번 돌려 채웁니다.
- 코드: `backend/app/domains/submissions/`, 마이그레이션 `0004` (`submissions.account`).

- (2026-11-13) 제출 건 응답의 `expenses[]` 에 `attendees`(참석자 목록)와 회의비의 `meeting_purpose`·`participant_count` 가 들어가고, 출장 건이면 `trip: { start_date, end_date, region, destination }` 이 함께 옵니다 (아니면 `null`). 직원 화면이 이 값으로 회의록·출장보고서·출장원 입력 칸을 채웁니다.
- (2026-11-13) 제출 건 응답에 `submitted_time`(분 단위 제출 시각, 예: `2026-11-13T17:55+09:00`)이 추가됐습니다. `submitted_at`(날짜)은 그대로입니다. 관리자 화면이 이 값으로 "방금 전"·"새 제출" 표시와 최근 제출 순 정렬을 합니다.

### 3-10. 로그인 · 회원가입 (`/api/auth/*`) — 2026-11-12 PM 요청, 백엔드·프론트 구현 완료

로그인 화면에서 사번(또는 이메일)과 비밀번호로 들어갑니다. **그 외 모든 API 는 `Authorization: Bearer <token>` 헤더로 사용자를 구분**하고,
예전 `X-Employee-No` 헤더는 없앴습니다 (보내도 무시되고 401). 토큰은 7일 뒤 만료되며 서버는 토큰을 저장하지 않습니다 (`AUTH_SECRET` 으로 서명).

| 하는 일 | 방식 | 주소 | 보내는 것 | 받는 것 |
|---|---|---|---|---|
| 회원가입 | POST | `/api/auth/signup` | `{ name, employee_no, department, grade, email, password }` | 로그인과 같은 모양 (201) |
| 로그인 | POST | `/api/auth/login` | `{ login_id, password }` — `login_id` 는 사번 또는 이메일 | `{ token, user: { employee_no, name, department, grade, role } }` |
| 내 계정 | GET | `/api/auth/me` | (토큰) | `user` 와 같은 모양 |

- 회원가입은 **항상 직원(`employee`) 역할**로 만들고, 관리자는 가입으로 만들 수 없습니다 (시드로만). 사번·이메일이 이미 있으면 409.
  비밀번호는 4자 이상, 이메일은 `a@b.c` 모양만 확인합니다. 사번은 대문자로, 이메일은 소문자로 저장합니다.
- 로그인 실패는 401 이고, **사번이 없는 경우와 비밀번호가 틀린 경우를 구분하지 않습니다** (같은 메시지).
- 토큰이 없으면 `{"error": "로그인이 필요합니다."}`, 잘못되거나 만료면 `{"error": "로그인이 만료되었거나 올바르지 않습니다. …"}` (둘 다 401). 프론트는 이때 세션을 지우고 로그인 화면으로 돌립니다.
- **DB 변경**: `users` 에 `email`(unique)·`password_hash` 추가 (alembic `0005`). 시드 계정 5개는 이메일 `<사번 소문자>@kobc.example`, 비밀번호 **`nova1234`** (`scripts/seed.py` 의 `DEMO_PASSWORD`).
  **팀원 로컬 DB 는 `uv run alembic upgrade head` → `uv run python -m scripts.seed` 를 다시 실행해야** 로그인됩니다 (시드는 비밀번호가 없는 기존 계정에만 채우므로 다른 데이터는 그대로).

```bash
curl -s -X POST localhost:8000/api/auth/login -H 'Content-Type: application/json' -d '{"login_id":"E1001","password":"nova1234"}'
# {"token":"RTEwMDE.1764...,"user":{"employee_no":"E1001","name":"노은비",...,"role":"employee"}}
curl -s localhost:8000/api/checklists -H 'Authorization: Bearer <token>'
```

---

### 3-11. 문서 작업 · 증빙 서류 보내기 (`/api/documents`) — 2026-11-16 양식·보내기 추가

직원이 쓰는 서류(출장보고서 · 회의록 · 출장원 · **지출결과서**)를 저장하고, 정산 건의 증빙으로 관리자에게 보냅니다.

| 하는 일 | 방식 | 주소 | 프론트가 보내는 것 |
|---|---|---|---|
| 내 서류 목록 | GET | `/api/documents` | 없음 |
| 새 서류 | POST | `/api/documents` | `{ kind, fields, title?, submission_code? }` |
| 저장 · 확인 | PATCH | `/api/documents/{id}` | `{ fields?, draft?, title?, confirmed? }` |
| 줄글 초안 | POST | `/api/documents/{id}/draft` | 없음 (정산 건 없이 따로 쓴 출장보고서 · 회의록, 출장원) |
| 양식 보기 | GET | `/api/documents/{id}/form` | 없음 (양식 서류) |
| AI 가 쓰는 칸 채우기 | POST | `/api/documents/{id}/fill` | 없음 (양식 서류) |
| 관리자에게 보내기 | POST | `/api/documents/{id}/send` | 없음 |
| 삭제 | DELETE | `/api/documents/{id}` | 없음 |
| (관리자) 정산 건의 첨부 서류 | GET | `/api/admin/submissions/{code}/documents` | 없음 |

- `submission_code`(제출 번호)를 주면 그 정산 건에 붙습니다. 내가 낸 건만 되고, 남의 건이면 404.
- 응답(서류 한 건)에 `submission_code`, `sent_at`(보낸 시각, 안 보냈으면 `null`)이 추가됐습니다.
- **보내기 조건**: 정산 건에 붙은 서류 + `confirmed: true`. 보낸 뒤 내용을 고치면 `confirmed`·`sent_at` 이 풀려서 다시 보내야 합니다 (관리자가 옛 내용을 보지 않게).
- **양식 서류** (기본 양식 3종): 지출결과서는 항상, 회의록 · 출장보고서는 **정산 건에 붙었을 때** 양식으로 만들어집니다.
  정산 건 없이 따로 쓴 회의록 · 출장보고서와 출장원은 예전처럼 줄글 초안(`/draft`)입니다.
  - 정산 건 하나에 같은 양식은 한 부입니다 (이미 있으면 그 서류를 돌려줌). 지출결과서는 정산 건에서만 만들 수 있습니다.
  - 금액 · 날짜 · 건명 · 부서 · 참석자는 저장하지 않고 정산 건에서 매번 읽습니다. `fields` 에는 직원이 고칠 수 있는 칸만 들어갑니다.
    - 지출결과서: `detail_0…`(상세내역), `use_0…`(용도), `inspector`(검사(수)자), `remark`(특이 사항)
    - 회의록: `content`(회의 내용)
    - 출장보고서: `destination`(출장지), `content`(출장 내용)
    - 공통: `ai_keys`(지금 값이 AI 가 쓴 그대로인 칸 목록. 직원이 고치면 프론트가 빼서 보냄)
  - `GET …/form` 응답: `{ kind, submission_code, sheets: [{ title, blocks: [...] }], todo[], ready }`. 블록 종류:
    `info`(머리표 `rows:[{label, cell}]`) · `table`(`caption?, columns, rows, total?`) · `field`(넓은 글 칸 `label, cell`) ·
    `note`(`text, style`) · `signers`(`rows:[{role, cell}]`) · `evidence`(`title, items:[{date, label, payment, amount, receipt_id}]`) · `photos`(`title, hint`).
    칸 하나는 `{ value, source, align? }` 이고 고칠 수 있는 칸에는 `key, label, required, placeholder, ai, multiline, limit` 가 더 붙습니다.
    `source` 는 `auto`(정산 건에서 가져옴) / `ai`(AI 가 씀) / `manual`(직접 입력) / `blank`(서명 · 사진, 시스템 밖) 입니다.
    `todo` 는 꼭 채워야 하는데 비어 있는 칸 목록이고, 비어 있으면 `confirmed: true` 가 400 으로 막힙니다.
  - `POST …/fill`: 지출결과서는 상세내역 · 용도 문구를 다시 제안하고, 회의록 · 출장보고서는 직원이 적은 `content` 메모를 보고서 문체로 다듬습니다.
    다듬은 글의 숫자(날짜 · 인원 · 금액)가 원래 글과 달라지면 쓰지 않고 그대로 둡니다. 직원이 직접 고친 칸은 건드리지 않습니다.
  - `evidence` 의 `receipt_id` 는 보관해 둔 영수증 사진 번호입니다 (아래 영수증 사진 참고). 제출한 사람이 올린 사진만 붙고, 없으면 `null`.
  - 칸 구성은 `backend/app/domains/documents/forms.py` 한 곳에서 정합니다.
- 관리자 응답: `{ expected: [종류], missing: [종류], documents: [{ id, kind, title, writer, sent_at, draft, form }] }`.
  `expected` 는 정산 유형별로 받아야 하는 서류입니다 (출장: 지출결과서 · 출장보고서 / 회의비: 지출결과서 · 회의록 / 그 밖: 지출결과서).
  보내지 않은 서류는 관리자에게 보이지 않습니다.
- (2026-11-16) **반려 사유를 직원에게 항목별로 · 고쳐서 다시 제출**
  - `POST /api/admin/submissions/{code}/decision` 요청에 `issues: [{ field, verdict, message, basis, fix }]` 를 실을 수 있습니다 (반려할 때 관리자가 고른 사유 항목). 안 보내면 예전처럼 AI 판정의 문제 항목 전체가 기록됩니다.
  - 제출 건 응답에 `decision_issues`(반려 사유 항목, 반려가 아니면 `[]`), `resubmit_of`(고쳐서 다시 낸 건이면 원래 반려 건 번호), `resubmitted_as`(이 반려 건을 고쳐 다시 낸 새 번호, 목록·상세 응답에만)가 추가됐습니다.
  - `POST /api/submissions` 요청에 `resubmit_of: "S-2026-175"` 를 실으면 그 반려 건의 재제출로 기록됩니다. 내가 낸 반려 건이 아니면 400.
  - 응답의 `expenses[]` 에 `merchant_type`, `trip` 에 `vehicle` 이 추가됐습니다 (다시 제출할 때 그대로 이어받기 위함).
- (2026-11-16) 제출 건 응답(`/api/submissions`, `/api/admin/submissions`, `/api/admin/submissions/{code}`)에 서류 상태 `docs: { expected: [종류], sent: [종류], missing: [종류] }` 가 함께 옵니다.
  관리자 목록 · 홈의 "서류 1/2 · 서류 미제출" 표시가 이 값을 씁니다. `sent` 는 직원이 보내기까지 마친 서류만 셉니다.
- **영수증 사진** (2026-11-16): 로그인한 상태로 `POST /api/receipt` 를 부르면 사진을 보관하고 응답에 `receipt_id` 를 함께 돌려줍니다 (로그인 없이 부르면 보관하지 않음).
  프론트는 이 번호를 청구 항목에 실어 제출하고(`items[].receipt_id`), 양식의 증빙 사진 칸이 `GET /api/receipts/{id}/image` 로 사진을 받습니다 (올린 본인 · 회계 관리자만, 그 밖에는 404).
  사진은 `backend/data/uploads/receipts/` 에 저장되고 저장소에는 올라가지 않습니다 (`.gitignore`).

---

### 3-12. 지출내역 엑셀 (`GET /api/ledger`, `GET /api/admin/ledger`) — 2026-11-16 추가

제출한 정산 건의 지출 항목을 한 줄씩 정리한 엑셀(.xlsx) 파일을 돌려줍니다. JSON 이 아니라 파일입니다.

| 하는 일 | 방식 | 주소 | 누가 |
|---|---|---|---|
| 내 정산 건의 지출내역 | GET | `/api/ledger` | 로그인한 직원 |
| 전체 제출 건의 지출내역 | GET | `/api/admin/ledger` | 회계 관리자 (아니면 403) |

- 표 구성: No · 구분(정산 유형) · 집행유형(계정과목, 없으면 "미입력") · 집행부서(관리자 파일은 "부서 성명") · 내용(품명 · 건명) · 금액 · 비고(제출 번호 · 지출일 · 상태).
- 지출 한 건이 한 줄입니다 (합치지 않음). 지출일 순으로 정렬하고, **반려한 정산은 넣지 않습니다**.
- 아래에 정산 유형별 소계와 합계가 붙습니다. 엑셀 수식(`SUMIF`, `SUM`)이라 줄을 고치면 다시 계산되고, 계산값도 함께 저장해서 수식을 계산하지 않는 미리보기에서도 숫자가 보입니다.
- 프론트는 토큰을 실어 받아서 `지출내역_YYYYMMDD.xlsx` 로 저장합니다 (`downloadLedger`, `components/LedgerButton.jsx`). 버튼은 직원의 "내 정산 현황"과 관리자의 "정산 검토 대기함"에 있습니다.
- 만드는 코드는 `backend/app/domains/ledger/excel.py` (라이브러리 `xlsxwriter`).

### 3-15. 출장 신청 (`/api/trips`) — 2026-11-23 추가 (2026-11-20 코칭: 신청 → 정산 → 보고서)

출장 전에 목적·기간·장소·교통을 등록합니다. 다녀와서 출장 정산을 시작할 때 이 값을 그대로 불러와 잠그고,
정산을 제출할 때 `trip_id` 를 함께 보내면 새 출장을 만들지 않고 신청한 출장에 붙습니다. 그래서 출장보고서가 목적·일시·출장지를 이어받습니다.
실제 결재는 하지 않으므로 신청하면 바로 `신청` 상태입니다. 모두 로그인한 본인의 출장만 다룹니다.

| 하는 일 | 방식 | 주소 |
|---|---|---|
| 출장 신청 | POST | `/api/trips` |
| 내 출장 목록 (취소 제외, 시작일 최근 순) | GET | `/api/trips` |
| 한 건 보기 | GET | `/api/trips/{id}` |
| 신청 취소 (정산 전만, 정산했으면 409) | DELETE | `/api/trips/{id}` |

요청 (POST)

```json
{
  "trip_type": "국내출장",
  "purpose": "부산 선사 방문 · 선박금융 상담",
  "destination": "부산광역시 강서구 신항로 1",
  "start_date": "2026-12-03",
  "end_date": "2026-12-04",
  "vehicle": "대중교통",
  "private_car_approved": false,
  "distance_km": 18.5
}
```

- `trip_type`: `국내출장` / `근무지 내 출장`. `vehicle`: `대중교통` / `업무용차량` / `렌트차량` / `자가용`.
- `region`(서울 / 광역시 / 기타)을 비우면 출장지 주소로 정합니다 (`서울…` → 서울, `○○광역시`·부산·대구·인천·광주·대전·울산 → 광역시, 나머지 → 기타).
- `distance_km` 는 사무실 → 출장지 **편도** 거리(경로 조회 결과). 자가용 정산의 운행거리(근무지 내 출장은 왕복 거리)는 이 값의 왕복으로 채우고 잠급니다.
- `education`(교육 출장, 일비 2일 한도)과 `private_car_approved`(자가용 사전 승인)는 정산에서 잠깁니다.
- `hours`: 근무지 내 출장의 **예상** 출장 시간(4시간 기준). 정산에서 불러오되 실제 시간으로 고칠 수 있습니다.

응답 (한 건)

```json
{
  "id": 21, "trip_type": "국내출장", "purpose": "부산 선사 방문 · 선박금융 상담",
  "destination": "부산광역시 강서구 신항로 1", "region": "광역시",
  "start_date": "2026-12-03", "end_date": "2026-12-04",
  "vehicle": "대중교통", "private_car_approved": false, "distance_km": 18.5,
  "status": "신청",
  "stage": "출장 예정",
  "submission": null
}
```

- `stage` 는 저장하지 않고 매번 계산합니다: `출장 예정`(시작 전) → `출장 중` → `정산 전`(끝난 뒤, 정산 없음) → `정산 제출`(이 출장으로 낸 정산이 있음).
- `submission`: 이 출장으로 낸 가장 최근 정산 `{ "id": "S-2026-002", "status": "검토 대기", "verdict": "규정상 확인 가능" }`.
- 정산 제출(3-9)에 `"trip_id": 21` 을 넣으면 그 출장에 연결됩니다. 건명(`purpose`)을 비우면 신청한 목적이 건명이 됩니다. 취소한 출장이나 남의 출장이면 400 / 404.
- 코드: `backend/app/domains/trips/`, 화면: `pages/TripRequestPage.jsx`(신청), `pages/HomePage.jsx`(내 출장), `pages/TravelCalcPage.jsx`(불러오기·잠금).

---

## 4. 에러일 때 돌려주는 모양 (함께 정할 것)

백엔드가 실패했을 때도 프론트가 "문제가 생겼습니다"를 띄워야 합니다. 아래처럼 통일하면 프론트는 성공/실패 두 경우만 처리하면 됩니다.

| 상황 | HTTP 상태코드 | 본문 |
|---|---|---|
| 프론트가 잘못 보냄 (필수 값 빠짐 등) | 400 | `{ "error": "items가 비어 있습니다." }` |
| 백엔드 내부 오류 | 500 | `{ "error": "검증 중 오류가 발생했습니다." }` |

**요청 한 줄:** 에러일 때는 본문에 `error` 라는 이름으로 사람이 읽을 수 있는 설명 문장을 넣어주세요.

---

## 5. 서로 기다리지 않는 작업 규칙 (함께 정할 것)

- **백엔드가 늦어도 프론트는 멈추지 않습니다.**
  프론트는 "목업 모드"를 넣어서, 백엔드 없이도 3번에서 정한 모양의 가짜 응답으로 화면을 만듭니다. 그래서 3번 모양만 안 바뀌면 됩니다.

- **프론트가 늦어도 백엔드는 멈추지 않습니다.**
  FastAPI라면 `http://localhost:8000/docs` 에 자동으로 테스트 화면이 생깁니다. 브라우저 없이도 API를 눌러볼 수 있고, 저도 그 화면을 보고 응답 모양을 확인할 수 있어서 켜두시면 좋습니다.

- **데이터 모양이 바뀌면 바꾸기 전에 알려주기.**
  필드 이름 하나만 바뀌어도 프론트가 깨집니다. 팀 채널에 한 줄만 올려주시면 됩니다.

- **저장소 구조 제안.**
  깃 저장소 하나에 `frontend/` 와 `backend/` 폴더로 나누는 걸 제안합니다. 각자 자기 폴더만 건드리면 충돌이 안 납니다.

- **합의한 내용은 한 곳에 적어두기.**
  이 문서를 저장소 루트에 `API.md` 같은 이름으로 넣어두고, 바뀌면 여기만 고치면 됩니다.

---

## 6. 시작 순서 (이 순서대로 하면 됩니다)

| 순서 | 할 일 | 누가 |
|---|---|---|
| 1 | 1번 표 채워서 알려주기 | 백엔드 |
| 2 | CORS 허용 넣기 | 백엔드 |
| 3 | 3번 API 주소·데이터 모양 보고 "이대로 OK" 또는 수정 의견 주기 | 백엔드 |
| 4 | 4번 에러 모양 OK | 백엔드 |
| 5 | 합의된 모양으로 목업 응답 만들고 화면 제작 시작 | 프론트 |
| 6 | 3개 API를 우선 "고정된 가짜 데이터"라도 돌려주는 상태로 만들기 (실제 검증 로직은 나중에) | 백엔드 |
| 7 | 제 노트북에서 백엔드 켜고 프론트 연결 테스트 | 둘이 함께 |

> 6번이 핵심입니다.
> 처음부터 실제 규정 검증을 구현하지 않아도 됩니다. 3번 예시 JSON을 그대로 돌려주는 API 3개만 있으면 "연결"은 끝나고, 그 뒤에 각자 기능을 얹을 수 있습니다. 이게 회의에서 말한 "베이스코드 먼저, 기능은 나중에"입니다.

---

## 7. 참고: 목업 데이터에 쓸 검증 사례

프론트 목업과 백엔드 가짜 응답에 같은 사례를 쓰면 나중에 비교가 쉽습니다. 규정 정리본(`regulations/별표1_국내여비지급표_정리본.md`)에서 바로 쓸 수 있는 사례입니다.

| 사례 | 판정 | 근거 조항 | 수정 방법 |
|---|---|---|---|
| 조식 포함 숙박인데 식비 전액 청구 | 보완 필요 | 여비규정 제11조 제4항 | 식비 1/3 차감 |
| 자가용 이용, 사전 승인 없음 | 담당자 확인 필요 | 여비규정 제13조 제5항 | 승인 여부 확인 |
| 동승자가 교통비 별도 청구 | 보완 필요 | 여비규정 제13조 제7항 | 동승자 교통비 삭제 |
| 공용차량 이용 시 일비 전액 청구 | 보완 필요 | 여비규정 제14조 제1항 | 일비 1/2로 수정 |
| 출장 종료 후 15일 초과 정산 | 담당자 확인 필요 | 여비규정 제3조의2 제2항 | 지연 사유 확인 |
| 법인카드 23시~06시 사용 | 보완 필요 | 법인카드 지침 제10조 제4항 | 별지 제5호 사유서 첨부 |
| 업무추진비 50만원 이상 사전결재 없음 | 보완 필요 | 업무추진비 지침 제3조 제4항 | 사전결재 문서 첨부 |

---

궁금한 점이나 "이건 이렇게 하는 게 더 편하다" 싶은 부분은 편하게 말씀해 주세요. 같이 정하는 게 목적이라 제안은 다 바뀌어도 괜찮습니다.
