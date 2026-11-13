# 경비 정산 사전검증 에이전트

KTcs 미래내일 일경험 · 팀 NOVA
한국해양진흥공사 법인카드·국내출장 경비를 제출 전에 규정 기준으로 검증하는 에이전트

## 폴더 구조

```
nova-fin-assistant/
├── frontend/   # React (Vite) 화면        ← 프론트엔드 담당
├── backend/    # FastAPI API 서버 + RAG   ← 백엔드 담당
└── docs/       # 연동 약속(API.md), 진행 보고
```

## 현재 상태 (2026-11-03)

프론트엔드 · 백엔드 **베이스코드** 단계입니다. 화면 틀, API 서버, DB, RAG 뼈대가 갖춰져 있고 기능은 이제 얹는 단계입니다.

| 구분 | 상태 |
|---|---|
| 규정 Q&A · 청구 검증 · 체크리스트 화면 틀 | 완료 |
| 백엔드 호출 모듈 + 목업 모드 | 완료 |
| 검증 결과 카드 (판정 3단계) | 완료 |
| 영수증 등록 화면 (U-06) — 샘플 11장 + 내 사진 + 카메라 촬영, 인식값 수정, 지출 건 초안, "청구 검증으로 보내기"(법인카드 건으로 U-04 폼에 채움) | 완료 (실제 인식은 백엔드 `POST /api/receipt`, 공용 OpenAI 키 · 11/10 / 샘플 사진·응답 개인정보 마스킹 · 11/10) |
| 관리자 정산 검토 대기함 (M-01) 와이어프레임 | 완료 (목업 데이터) |
| 관리자 홈 — 들어오자마자 제출 / 검토 대기 / 확인 필요 건수(확인 필요는 빨간 배경 + ⚠, 반려 포함)와 확인 필요 목록 8건. 숫자 카드·행을 누르면 검토 대기함의 그 보기·그 건으로 이동 | 완료 (11/13 코칭 반영. 홈과 검토 대기함이 같은 기준을 쓰도록 `pages/admin/reviewQueue.js` 로 통일) |
| 로그인·회원가입 화면 — 사번(또는 이메일)+비밀번호로 `POST /api/auth/login`, 가입은 항상 직원 역할. 모든 API 는 `Authorization: Bearer <token>` 으로 사용자 구분 (`X-Employee-No` 제거) | 완료 (11/12 PM 요청. 시드 계정 비밀번호 `nova1234`, 팀원은 `alembic upgrade head` + 시드 재실행 필요. `docs/API.md` 3-10) |
| 시연용 관리자 검토함 데이터 — 출장 27건 + 점심·회식·회의비 17건 (가상 직원 44명) | 완료 (`backend/scripts/seed_demo.py` → `scripts/data/demo_submissions.json`·`demo_meet_cases.json`. 11/10 패키지 + 종원 11/12 자료. AI 판정은 엔진 실제 결과, 기대와 다른 건은 적재 시 출력. FAQ 22개는 `data/eval/qa_eval.csv`. `docs/U-04_점심회식회의비_확장.md`) |
| 정산 제출 → 관리자 검토 대기함 실제 연결 — 직원이 검증 결과를 제출(건명·계정과목)하면 DB 에 저장되어 관리자 목록·상세에 뜨고 승인/반려·반려 초안(LLM) 저장 | 완료 (`/api/submissions`, `/api/admin/submissions/*`) |
| 관리자 계정과목 검토 카드 (M-05) — 직원 입력 vs AI 제안 비교, 불일치면 반려 사유 후보 추가 | 완료 (제안은 `POST /api/voucher-draft` 재사용, 목록·상세는 목업) |
| 백엔드 서버 · DB(PostgreSQL + pgvector) · 실행 스크립트 | 완료 |
| 규정 Q&A RAG (규정 적재 → 검색 → 답변 + 근거 조항) | 뼈대 완료 |
| 청구 검증 규칙 엔진 연결 (`backend/app/precheck`, 규칙 36개 · 테스트 41개) | 완료 |
| 청구 검증 입력 폼 (U-04 최소 세트 + 좌석 등급) | 완료 |
| 출장비 계산 화면 (U-05) — 출장 정보 입력 → 항목별 금액·계산식·근거, "청구 검증으로 보내기"(계산 결과로 U-04 폼에 채움) | 완료 (`POST /api/travel-calc`) |
| Q&A 채팅, 체크리스트 내용 | 다음 단계 |
| 실제 백엔드 연결 테스트 | 가능 (아래 실행 방법) |

체크리스트 응답은 아직 `(예시)`가 붙은 가짜 데이터입니다. 청구 검증은 규칙 엔진이 실제로 판정합니다.

## 빠른 시작

백엔드를 켠 뒤 프론트를 연결 모드로 실행합니다.

```powershell
# 1) 백엔드 (backend 폴더)
cd backend
.\setup.cmd      # 처음 한 번
.\server.cmd     # 서버 켜기 → http://localhost:8000/docs

# 2) 프론트 (frontend 폴더, 새 터미널)
cd frontend
npm install      # 처음 한 번
npm run dev      # → http://localhost:5173
```

## 백엔드 실행

Docker Desktop 과 uv 가 필요합니다. 설치 방법과 자세한 내용은 [backend/README.md](backend/README.md) 를 봅니다.

```powershell
cd backend
.\setup.cmd      # 처음 한 번: DB 켜기 · 테이블 생성 · 데모 데이터 · 규정 적재
.\server.cmd     # 서버 켜기 (DB 자동 켜기 · 테이블 자동 최신화) · 끄기는 Ctrl+C
```

- 서버: http://localhost:8000 · API 테스트 화면: http://localhost:8000/docs
- `backend/.env` 의 `OPENAI_API_KEY` 를 비우면 목업 AI 로 동작합니다.

## 프론트엔드 실행

### 1. 설치 (처음 한 번)

Node.js 18 이상이 필요합니다.

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

백엔드 서버(`backend\server.cmd`)를 켠 상태에서, `frontend/.env.local` 파일을 만들고 아래 두 줄을 적은 뒤 `npm run dev` 를 다시 실행합니다.

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
│   ├── client.js           # 백엔드 호출 함수 (askQa, getProcedure, verifyClaim, getChecklist)
│   └── mock.js             # 목업 모드 응답
├── mocks/                  # 가짜 응답 JSON (verify / qa / qa-ungrounded / procedure / checklist)
├── components/
│   ├── Layout.jsx          # 상단 헤더 + 탭 메뉴
│   ├── VerdictBadge.jsx    # 판정 3단계 뱃지
│   ├── ResultCard.jsx      # 검증 결과 카드 한 장
│   ├── VerifyResult.jsx    # 종합 판정 + 카드 목록
│   ├── LoginPage.jsx (pages/)  # 로그인·회원가입 → 역할별 화면 (auth/accounts.js 가 세션 저장·시연 계정 안내)
│   ├── QaAnswer.jsx        # 규정 Q&A 답변 (본문 [1] 인용 ↔ 근거 목록 연결)
│   ├── ProcedureGuide.jsx  # 업무절차 안내 (필요 서류 · 순서 · 기한 · 결재자)
│   ├── SourceList.jsx      # 근거 조항 목록 (조항 · 개정일 · 원문 링크)
│   └── GroundNotice.jsx    # 근거 있음 뱃지 / "담당자 확인 필요" 경고
└── pages/
    ├── QaPage.jsx          # 규정 Q&A · 업무절차 안내 (U-01 · U-02 · U-03)
    ├── VerifyPage.jsx      # 청구 검증
    ├── TravelCalcPage.jsx  # 출장비 계산 (U-05)
    └── ChecklistPage.jsx   # 체크리스트
```

### 기능을 얹을 때

- **백엔드에 요청**하려면 `api/client.js` 의 함수를 부릅니다. 주소·에러 처리는 신경 쓰지 않아도 됩니다.
- **검증 결과를 보여주려면** `<VerifyResult result={...} />` 에 응답 JSON을 그대로 넣습니다.
- **화면을 추가하려면** `pages/` 에 파일을 만들고 `App.jsx` 의 `PAGES` 에 한 줄 추가합니다.
- **색을 바꾸려면** `index.css` 맨 위의 변수만 고칩니다.

## 백엔드 코드 안내

```
backend/app/
├── main.py      # 시작점 · 라우터 등록 (기능 추가는 여기 한 줄)
├── core/        # 설정 · DB 연결 · 에러 형식
├── models/      # DB 테이블
├── ai/          # OpenAI 호출 (LLM · 임베딩 · 마스킹)
├── rag/         # 규정 적재 · 검색 · 답변
├── precheck/    # 규칙 엔진
└── domains/     # 기능별 API (qa · verify · checklist)
```

### 기능을 얹을 때

- **API를 추가하려면** `domains/` 에 폴더를 만들고 `main.py` 에 라우터 한 줄 추가합니다.
- **OpenAI를 부를 때**는 `app/ai/` 의 함수만 씁니다.
- **에러를 돌려줄 때**는 `raise AppError("메시지", 상태코드)` 를 씁니다.

## 프론트·백엔드 사이 약속

API 주소, 요청·응답 JSON 모양, 에러 형식, 판정 값 3가지는
[docs/API.md](docs/API.md) 를 기준으로 합니다. 모양을 바꿀 때는 바꾸기 전에 팀 채널에 알립니다.

| 기능 | 방식 | 주소 |
|---|---|---|
| 규정 Q&A | POST | `/api/qa` |
| 청구 검증 | POST | `/api/verify` |
| 출장비 계산 | POST | `/api/travel-calc` |
| 체크리스트 | GET | `/api/checklist?type=국내출장` |

판정 값: `규정상 확인 가능` · `보완 필요` · `담당자 확인 필요`

## 작업 방식

- `frontend/` 는 프론트엔드 담당, `backend/` 는 백엔드 담당이 각자 자기 폴더만 수정합니다.
- 작업은 `feature/이름` 브랜치에서 하고, Pull Request로 main에 합칩니다.
- 새 작업은 최신 `main` 에서 브랜치를 따서 시작합니다. (`git checkout main` → `git pull` → `git checkout -b feature/이름`)
- PR 은 **"Create a merge commit"** 으로 합칩니다. (Squash 하면 기록이 끊겨 다른 브랜치와 충돌이 납니다)
- `.env` 처럼 API 키가 들어가는 파일은 커밋하지 않습니다.
