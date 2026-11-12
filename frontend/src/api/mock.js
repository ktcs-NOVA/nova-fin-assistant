// 목업 모드: 백엔드 없이 JSON 파일을 돌려줍니다.
// 응답 모양은 docs/API.md 3번과 같습니다. 백엔드는 이 JSON과 같은 모양으로 응답하면 됩니다.
// 내용은 전부 "(예시)" 가짜 데이터이며, 실제 판정은 백엔드가 합니다.

import qaData from '../mocks/qa.json'
import qaUngroundedData from '../mocks/qa-ungrounded.json'
import procedureData from '../mocks/procedure.json'
import checklistData from '../mocks/checklist.json'
import receiptsData from '../mocks/receipts.json'
import { DEMO_ACCOUNTS, DEMO_PASSWORD, ROLE } from '../auth/accounts.js'

// 실제 서버처럼 잠깐 기다렸다가 응답 (로딩 표시를 테스트하기 위해)
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

// 이 단어가 들어간 질문은 "근거 없음" 응답을 돌려줘서 경고 화면(U-03)을 확인할 수 있게 합니다.
const UNGROUNDED_WORDS = ['주차', '연차', '휴가']

// 이 단어가 들어간 질문은 절차 안내(U-02) 응답을 돌려줍니다. 실제로는 백엔드의 챗봇이 고릅니다.
const PROCEDURE_WORDS = ['절차', '준비', '해야', '다음', '처리']

export async function askQa(question) {
  await wait(600)
  if (!question?.trim()) throw new Error('질문을 입력해 주세요.')
  if (UNGROUNDED_WORDS.some((w) => question.includes(w))) return { type: 'answer', ...qaUngroundedData }
  if (PROCEDURE_WORDS.some((w) => question.includes(w))) {
    return {
      type: 'procedure',
      answer: procedureData.summary,
      grounded: true,
      sources: procedureData.sources,
      procedure: procedureData,
    }
  }
  return { type: 'answer', ...qaData }
}

export async function getProcedure(task) {
  await wait(700)
  if (!task?.trim()) throw new Error('알고 싶은 업무를 입력해 주세요.')
  return procedureData
}

// 청구 검증: 실제 판정은 백엔드(PM이 만든 precheck 엔진)가 합니다.
// 목업은 규칙을 흉내 내지 않고, 입력한 항목마다 "(예시)" 표시만 돌려줍니다.
export async function verifyClaim(claim) {
  await wait(800)
  if (!claim?.items?.length) throw new Error('청구 항목이 비어 있습니다.')
  return {
    overall: '담당자 확인 필요',
    items: claim.items.map((it) => ({
      field: it.field,
      verdict: '담당자 확인 필요',
      message: `(예시) ${it.amount.toLocaleString('ko-KR')}원 — 목업 모드에서는 규정 판정을 하지 않습니다. 백엔드 연결 시 실제 판정이 표시됩니다.`,
      basis: '(예시)',
      fix: '',
    })),
  }
}

export async function getChecklist(type = '국내출장') {
  await wait(300)
  return { ...checklistData, type }
}

// 내 체크리스트: 목업에서는 새로고침하면 사라집니다.
let savedChecklists = []
let nextSavedId = 1

export async function getChecklists() {
  await wait(300)
  return structuredClone(savedChecklists)
}

export async function createChecklist(task) {
  await wait(300)
  const { summary, deadline, approver, sources, documents, steps } = procedureData
  const rows = [
    ...documents.map((d) => ({ kind: 'document', title: d.name, detail: d.detail, basis: d.basis })),
    ...steps.map((s) => ({ kind: 'step', title: s.title, detail: s.detail, basis: s.basis })),
  ]
  const checklist = {
    id: nextSavedId++,
    task,
    summary,
    deadline,
    approver,
    sources,
    created_at: new Date().toISOString(),
    items: rows.map((row) => ({ ...row, id: nextSavedId++, done: false, done_at: null })),
  }
  savedChecklists = [checklist, ...savedChecklists]
  return structuredClone(checklist)
}

export async function updateChecklistItem(checklistId, itemId, done) {
  await wait(150)
  const item = savedChecklists.find((c) => c.id === checklistId)?.items.find((i) => i.id === itemId)
  if (!item) throw new Error('체크 항목을 찾을 수 없습니다.')
  item.done = done
  item.done_at = done ? new Date().toISOString() : null
  return structuredClone(item)
}

export async function deleteChecklist(checklistId) {
  await wait(150)
  savedChecklists = savedChecklists.filter((c) => c.id !== checklistId)
  return null
}

// 문서 작업: 목업은 이 브라우저(localStorage)에 저장해서 새로고침해도 남습니다. 초안 계산은 백엔드 drafts.py 와 같은 규칙이에요.
const DOCS_KEY = 'nova.mock.documents'
const DOC_REQUIRED = {
  출장보고서: { trip_start: '출장 시작일', trip_end: '출장 종료일', destination: '출장지', purpose: '출장 목적', work_notes: '주요 수행 내용' },
  회의록: { meeting_title: '회의명', meeting_date: '회의 일시', attendees: '참석자', notes: '논의 내용 메모' },
  출장원: { trip_start: '출장 시작일', trip_end: '출장 종료일', destination: '출장지', purpose: '출장 목적', total_amount: '정산 금액' },
}
const loadDocs = () => {
  try { return JSON.parse(localStorage.getItem(DOCS_KEY)) ?? [] } catch { return [] }
}
const saveDocs = (rows) => {
  try { localStorage.setItem(DOCS_KEY, JSON.stringify(rows)) } catch { /* 저장소를 못 쓰면 이번 화면에서만 유지 */ }
}
const num = (v) => { const n = Math.trunc(Number(v)); return Number.isFinite(n) ? n : 0 }
const won = (v) => `${num(v).toLocaleString('ko-KR')}원`
const ymd = (s) => { const [y, m, d] = String(s).slice(0, 10).split('-').map(Number); return y ? `${y}년 ${m}월 ${d}일` : String(s ?? '') }
const nightsOf = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000)
const periodText = (a, b) => {
  const n = nightsOf(a, b)
  if (Number.isNaN(n)) return `${a} ~ ${b}`
  return `${n <= 0 ? ymd(a) : `${ymd(a)} ~ ${ymd(b)}`} (${n <= 0 ? '당일' : `${n}박 ${n + 1}일`})`
}
const txt = (f, k) => String(f[k] ?? '').trim()

function mockDraftText(kind, f, who) {
  if (kind === '출장보고서') {
    const costs = [['교통비', 'transport_fee'], ['숙박비', 'lodging_fee'], ['일비', 'daily_fee'], ['식비', 'meal_fee']].filter(([, k]) => num(f[k]) > 0)
    const lines = ['국내출장 결과 보고서', '', `출장자: ${who}`, `출장 기간: ${periodText(f.trip_start, f.trip_end)}`, `출장지: ${txt(f, 'destination')}`, `출장 목적: ${txt(f, 'purpose')}`, '', '수행 내용', txt(f, 'work_notes')]
    if (costs.length) lines.push('', '경비 내역', ...costs.map(([l, k]) => `${l}: ${won(f[k])}`), `합계: ${won(costs.reduce((a, [, k]) => a + num(f[k]), 0))}`)
    return lines.join('\n')
  }
  if (kind === '회의록') {
    const people = (f.attendees ?? []).map((a) => String(a).trim()).filter(Boolean)
    const lines = ['회의록', '', `회의명: ${txt(f, 'meeting_title')}`, `일시: ${ymd(f.meeting_date)}`]
    if (txt(f, 'place')) lines.push(`장소: ${txt(f, 'place')}`)
    lines.push(`참석자: ${people.length}명 (${people.join(', ')})`)
    if (num(f.receipt_amount) > 0) lines.push(`회의 비용: ${won(f.receipt_amount)} · 1인당 ${won(Math.floor(num(f.receipt_amount) / people.length + 0.5))} (원 미만 반올림)`)
    return [...lines, '', '논의 내용', txt(f, 'notes'), '', `작성자: ${who}`].join('\n')
  }
  return ['출장원 (정산)', '', `출장자: ${who}`, `출장 기간: ${periodText(f.trip_start, f.trip_end)}`, `출장지: ${txt(f, 'destination')}`, `출장 목적: ${txt(f, 'purpose')}`, `정산 금액: ${won(f.total_amount)}`, '', `서명: ${txt(f, 'signer_name') || '(서명 전)'}`].join('\n')
}

export async function listDocuments() {
  await wait(200)
  return loadDocs().sort((a, b) => b.updated_at.localeCompare(a.updated_at))
}

export async function createDocument({ kind, title, fields }) {
  await wait(200)
  const rows = loadDocs()
  const now = new Date().toISOString()
  const detail = txt(fields ?? {}, 'destination') || txt(fields ?? {}, 'meeting_title')
  const doc = { id: Date.now(), kind, title: (title ?? '').trim() || (detail ? `${kind} · ${detail}` : kind), status: '작성 중', fields: fields ?? {}, draft: '', confirmed: false, created_at: now, updated_at: now }
  saveDocs([doc, ...rows])
  return structuredClone(doc)
}

export async function updateDocument(id, patch) {
  await wait(150)
  const rows = loadDocs()
  const doc = rows.find((d) => d.id === id)
  if (!doc) throw new Error('서류를 찾을 수 없습니다.')
  let changed = false
  if (patch.fields !== undefined && JSON.stringify(patch.fields) !== JSON.stringify(doc.fields)) { doc.fields = patch.fields; changed = true }
  if (patch.draft !== undefined && patch.draft !== doc.draft) { doc.draft = patch.draft; changed = true }
  if (patch.title?.trim()) doc.title = patch.title.trim()
  if (patch.confirmed === true) {
    if (!doc.draft.trim()) throw new Error('초안이 아직 없어서 확인 완료로 바꿀 수 없습니다.')
    doc.confirmed = true
  } else if (patch.confirmed === false || changed) doc.confirmed = false
  doc.status = doc.confirmed ? '작성 완료' : '작성 중'
  doc.updated_at = new Date().toISOString()
  saveDocs(rows)
  return structuredClone(doc)
}

export async function draftDocument(id) {
  await wait(500)
  const rows = loadDocs()
  const doc = rows.find((d) => d.id === id)
  if (!doc) throw new Error('서류를 찾을 수 없습니다.')
  const lacking = Object.entries(DOC_REQUIRED[doc.kind]).filter(([k]) => {
    const v = doc.fields[k]
    return v == null || String(v).trim() === '' || (Array.isArray(v) && !v.length) || (k === 'total_amount' && !num(v))
  }).map(([, label]) => label)
  if (lacking.length) throw new Error(`초안을 만들려면 먼저 입력해 주세요: ${lacking.join(', ')}`)
  doc.draft = mockDraftText(doc.kind, doc.fields, '데모 사용자 (재무팀)')
  doc.confirmed = false
  doc.status = '작성 중'
  doc.updated_at = new Date().toISOString()
  saveDocs(rows)
  return structuredClone(doc)
}

export async function deleteDocument(id) {
  await wait(150)
  saveDocs(loadDocs().filter((d) => d.id !== id))
  return null
}

// 경로 조회: 실제 거리는 네이버 지도 API가 계산합니다. 목업은 모양만 같은 예시값을 돌려줍니다.
export async function lookupRoute(destination) {
  await wait(500)
  return { destination, distance_km: 410, duration_min: 160 }
}

// 출장비 계산(U-05): 실제 계산은 백엔드(PM 의 travel_calc 엔진)가 합니다.
// 목업은 규칙을 흉내 내지 않고, 모양만 같은 "(예시)" 응답을 돌려줍니다.
export async function calcTravel(req) {
  await wait(600)
  const grade = req?.grade ?? '직원 3급 이하'
  const trip = req?.trip ?? {}
  return {
    grade,
    trip_type: req?.trip_type ?? '국내출장',
    region: trip.region ?? null,
    days: 2,
    nights: 1,
    lines: [
      { field: '일비', amount: 60000, type: '정액', formula: '(예시) 30,000원 × 2일', basis: '여비규정 제14조 제1항, 별표 1', note: '' },
      { field: '식비', amount: 54000, type: '정액', formula: '(예시) 27,000원 × 2일', basis: '여비규정 제14조 제1항, 별표 1', note: '' },
      { field: '숙박비', amount: 90000, type: '상한(실비)', formula: '(예시) 광역시 90,000원 × 1박', basis: '여비규정 제14조 제2항, 별표 1', note: '영수증 금액으로 실비 정산' },
    ],
    summary: { fixed_total: 114000, lodging_cap: 90000, transport_total: 0, estimated_max: 204000 },
    notes: ['(예시) 목업 모드에서는 규정 계산을 하지 않습니다. 백엔드 연결 시 실제 계산 결과가 표시됩니다.'],
    verify_request: {
      trip_type: '국내출장', grade, trip,
      items: [
        { field: '일비', amount: 60000 },
        { field: '식비', amount: 54000, days: 2 },
        { field: '숙박비', amount: 90000, nights: 1 },
      ],
    },
  }
}

// ---------- 관리자 (M-01 정산 검토 대기함) ----------

import submissionsData from '../mocks/submissions.json'

// 메모리 안에서만 바뀌는 상태 (새로고침하면 초기화)
const submissions = structuredClone(submissionsData.items)

// 직원 제출(목업): 목록 맨 앞에 새 건을 넣어 관리자 화면에서 바로 보이게 함
export async function createSubmission(claim, extra = {}) {
  await wait(500)
  const items = claim.items ?? []
  if (!items.length) throw new Error('items가 비어 있습니다.')
  const verify = extra.verify_result ?? (await verifyClaim(claim))
  const year = new Date().getFullYear()
  const seq = submissions.filter((s) => s.id.startsWith(`S-${year}-`)).length + 1
  const first = items[0]
  const sub = {
    id: `S-${year}-${String(seq).padStart(3, '0')}`,
    submitter: '박철환', dept: '총무인사부',  // 목업은 로그인 계정을 모름
    type: claim.trip_type,
    purpose: extra.purpose || (claim.trip?.region ? `${claim.trip.region} 출장 여비 정산` : `${claim.trip_type} 지출 정산`),
    merchant: first.merchant ?? null,
    date: first.date ?? claim.trip?.start_date ?? new Date().toISOString().slice(0, 10),
    time: first.time ?? null,
    amount: items.reduce((a, it) => a + Number(it.amount || 0), 0),
    account: extra.account ?? null,
    submitted_at: new Date().toISOString().slice(0, 10),
    step: 5, verdict: verify.overall, status: '검토 대기', items: verify.items,
  }
  submissions.unshift(sub)
  return sub
}

export async function listMySubmissions() {
  await wait(300)
  const mine = submissions.filter((s) => s.submitter === '박철환')
  return { total: mine.length, items: mine }
}

export async function listSubmissions() {
  await wait(400)
  return { total: submissions.length, items: submissions }
}

export async function getSubmission(id) {
  await wait(250)
  const found = submissions.find((s) => s.id === id)
  if (!found) throw new Error(`제출 건 ${id} 을(를) 찾을 수 없습니다.`)
  return found
}

export async function decideSubmission(id, decision, message = '') {
  await wait(400)
  const found = submissions.find((s) => s.id === id)
  if (!found) throw new Error(`제출 건 ${id} 을(를) 찾을 수 없습니다.`)
  found.status = decision          // '승인' | '반려'
  found.step = 6
  found.decision_message = message
  found.decided_at = new Date().toISOString().slice(0, 10)
  return found
}

// 반려 메시지 초안: 실제로는 백엔드가 RAG 근거로 작성합니다.
// 목업에서는 선택한 문제 항목의 근거·수정 방법을 그대로 이어 붙입니다.
export async function draftRejectMessage(id, issueFields, extraIssues = []) {
  await wait(700)
  const found = submissions.find((s) => s.id === id)
  if (!found) throw new Error(`제출 건 ${id} 을(를) 찾을 수 없습니다.`)
  const picked = [...found.items.filter((it) => issueFields.includes(it.field)), ...extraIssues]
  if (!picked.length) throw new Error('반려 사유를 하나 이상 선택해 주세요.')
  const lines = picked.map(
    (it, i) => `${i + 1}. [${it.field}] ${it.message}\n   - 근거: ${it.basis}\n   - 수정: ${it.fix || '담당자와 협의'}`,
  )
  return {
    message: `${found.submitter}님, 제출하신 ${found.purpose} 정산 건은 아래 사유로 반려되었습니다.\n\n${lines.join('\n')}\n\n수정 후 다시 제출해 주세요.`,
    sources: picked.map((it) => it.basis),
  }
}

// ---------- 계정과목 검토 (M-05) ----------
// 실제로는 백엔드 U-07 결의서 초안(suggest_account)이 정합니다. 목업은 같은 규칙을 단순화해 흉내 냅니다.
const ACCOUNT_RULES = [
  [['숙박', '식비', '일비', '교통', '운임', '철도', '항공', '자가용'], '여비교통비', '국내여비', '규정 확인', '예산세칙 제22조 제2항, 여비규정 제2조'],
  [['화환', '경조'], '업무추진비', '경조사비', '규정 확인', '업무추진비 및 조직관리비 집행 지침 제2조 제1항'],
  [['업무추진비', '간담회', '접대', '유관기관'], '업무추진비', '대외 업무협의·간담회', '규정 확인', '업무추진비 및 조직관리비 집행 지침 제2조 제1항'],
  [['회의', '다과', '회식'], '조직관리비', '부서운영비(회의·다과·회식)', '규정 확인', '업무추진비 및 조직관리비 집행 지침 제2조 제2항'],
  [['사무용품', '소모품', '문구'], '소모품비', '', '가정', 'KOBC 계정과목표 미공개 — 일반 공공기관 비용 과목으로 가정'],
  [['도서', '인쇄'], '도서인쇄비', '', '가정', 'KOBC 계정과목표 미공개 — 일반 공공기관 비용 과목으로 가정'],
]

export async function suggestAccount(sub) {
  await wait(500)
  const texts = sub.type === '국내출장' ? sub.items.map((it) => it.field) : [sub.purpose]
  for (const t of texts) {
    const hit = ACCOUNT_RULES.find(([words]) => words.some((w) => t.includes(w)))
    if (hit) {
      const [, account, subAccount, confidence, basis] = hit
      return { account, sub_accounts: subAccount ? [subAccount] : [], confidence, basis }
    }
  }
  return {
    account: '담당자 확인', sub_accounts: [], confidence: '가정',
    basis: '항목명만으로 과목을 정할 수 없음 — 회계책임자 확인 필요 (회계규정 시행세칙 제6조 제3항)',
  }
}

// ---------- 영수증 인식 (U-06) ----------
// 샘플 11장은 experiments/receipt-ocr 에서 실제 API로 뽑은 결과를 그대로 돌려줍니다.
// 샘플이 아닌 사진은 목업으로 인식할 수 없으므로 백엔드 연결 모드로 안내합니다.

export async function recognizeReceipt({ filename }) {
  await wait(1200)
  const found = receiptsData.samples.find((s) => s.file === filename)
  if (!found) {
    throw new Error('목업 모드에서는 샘플 사진 11장만 인식할 수 있습니다. 직접 올린 사진은 백엔드 연결 모드(VITE_USE_MOCK=false)에서 인식됩니다.')
  }
  return structuredClone(found.result)
}

// ---------- 로그인 (목업) ----------
// 시연 계정(auth/accounts.js)은 공통 비밀번호로 들어가고, 가입한 계정은 새로고침 전까지만 기억합니다.

const signedUp = []

export async function login(loginId, password) {
  await wait(400)
  const key = String(loginId ?? '').trim().toLowerCase()
  const user = [...DEMO_ACCOUNTS, ...signedUp].find(
    (a) => a.employee_no.toLowerCase() === key || (a.email ?? `${a.employee_no.toLowerCase()}@kobc.example`) === key,
  )
  const ok = user && (signedUp.includes(user) ? user.password === password : password === DEMO_PASSWORD)
  if (!ok) throw new Error('사번(또는 이메일)이나 비밀번호가 맞지 않습니다.')
  const { password: _pw, email: _em, ...out } = user
  return { token: `mock.${out.employee_no}`, user: out }
}

export async function signup({ name, employeeNo, department, grade, email, password }) {
  await wait(500)
  const no = String(employeeNo ?? '').trim().toUpperCase()
  if ([...DEMO_ACCOUNTS, ...signedUp].some((a) => a.employee_no === no)) throw new Error(`이미 가입된 사번입니다: ${no}`)
  const user = { employee_no: no, name: name.trim(), department: department.trim(), grade, role: ROLE.EMPLOYEE, email: email.trim().toLowerCase(), password }
  signedUp.push(user)
  return login(no, password)
}
