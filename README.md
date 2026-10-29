# 경비 정산 사전검증 에이전트

KTcs 미래내일 일경험 · 팀 NOVA
한국해양진흥공사 법인카드·국내출장 경비를 제출 전에 규정 기준으로 검증하는 에이전트

## 폴더 구조

```
expense-agent/
├── frontend/   # React (Vite) 화면  ← 프론트엔드 담당
└── backend/    # API 서버           ← 백엔드 담당 (추가 예정)
```

## 프론트엔드 실행

### 1. 설치 (처음 한 번)

```bash
cd frontend
npm install
```

### 2. 목업 모드로 실행 (백엔드 없이)

```bash
npm run dev
```

브라우저에서 http://localhost:5173 을 엽니다. 헤더에 **목업 모드** 뱃지가 보이면 가짜 응답(`src/mocks/*.json`)으로 동작하는 상태입니다.

### 3. 백엔드에 연결해서 실행

`frontend/.env.local` 파일을 만들고 아래 두 줄을 적은 뒤 `npm run dev` 를 다시 실행합니다.

```
VITE_API_BASE=http://localhost:8000
VITE_USE_MOCK=false
```

`.env.local` 은 깃에 올라가지 않으니 각자 PC에서 자유롭게 바꿔도 됩니다. 헤더 뱃지가 **백엔드 연결** 로 바뀝니다.

## 프론트엔드 코드 안내

```
frontend/src/
├── App.jsx                 # 메뉴 목록과 현재 화면 (화면 추가는 여기 한 줄)
├── index.css               # 디자인 토큰(색·폰트)과 공통 스타일
├── api/
│   ├── client.js           # 백엔드 호출 함수 3개 (askQa, verifyClaim, getChecklist)
│   └── mock.js             # 목업 모드 응답
├── mocks/                  # 가짜 응답 JSON (verify / qa / checklist)
├── components/
│   ├── Layout.jsx          # 상단 헤더 + 탭 메뉴
│   ├── VerdictBadge.jsx    # 판정 3단계 뱃지
│   ├── ResultCard.jsx      # 검증 결과 카드 한 장
│   └── VerifyResult.jsx    # 종합 판정 + 카드 목록
└── pages/
    ├── QaPage.jsx          # 규정 Q&A
    ├── VerifyPage.jsx      # 청구 검증
    └── ChecklistPage.jsx   # 체크리스트
```

### 기능을 얹을 때

- **백엔드에 요청**하려면 `api/client.js` 의 함수를 부릅니다. 주소·에러 처리는 신경 쓰지 않아도 됩니다.
- **검증 결과를 보여주려면** `<VerifyResult result={...} />` 에 응답 JSON을 그대로 넣습니다.
- **화면을 추가하려면** `pages/` 에 파일을 만들고 `App.jsx` 의 `PAGES` 에 한 줄 추가합니다.
- **색을 바꾸려면** `index.css` 맨 위의 변수만 고칩니다.

## 프론트·백엔드 사이 약속

API 주소, 요청·응답 JSON 모양, 에러 형식, 판정 값 3가지는
[docs/API.md](docs/API.md) 를 기준으로 합니다. 모양을 바꿀 때는 바꾸기 전에 팀 채널에 알립니다.

| 기능 | 방식 | 주소 |
|---|---|---|
| 규정 Q&A | POST | `/api/qa` |
| 청구 검증 | POST | `/api/verify` |
| 체크리스트 | GET | `/api/checklist?type=국내출장` |

판정 값: `규정상 확인 가능` · `보완 필요` · `담당자 확인 필요`
