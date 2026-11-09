// API 호출 모듈. 모든 화면은 이 파일의 함수만 사용합니다.
//
//   VITE_API_BASE  백엔드 주소 (기본 http://localhost:8000)
//   VITE_USE_MOCK  "true"면 백엔드 대신 src/mocks/*.json 사용
//
// 설정은 frontend/.env (공통) 또는 frontend/.env.local (내 PC 전용) 에 적습니다.

import * as mock from './mock.js'
import { loadUser } from '../auth/accounts.js'

export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

// 판정 값은 이 세 가지로 고정 (백엔드와 합의)
export const VERDICT = {
  OK: '규정상 확인 가능',
  FIX: '보완 필요',
  CHECK: '담당자 확인 필요',
}

// 공통 요청 함수: 성공이면 JSON을 돌려주고, 실패면 Error를 던집니다.
async function request(method, path, body) {
  let res
  try {
    // 로그인한 사번을 함께 보내 백엔드가 그 사람의 데이터(체크리스트 등)로 처리하게 함. 없으면 백엔드 기본 직원.
    const user = loadUser()
    res = await fetch(API_BASE + path, {
      method,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(user ? { 'X-Employee-No': user.employee_no } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error(`백엔드(${API_BASE})에 연결할 수 없습니다. 서버가 켜져 있는지 확인해 주세요.`)
  }

  if (!res.ok) {
    // 백엔드 에러 형식: { "error": "설명" }
    let message = `요청 실패 (HTTP ${res.status})`
    try {
      const data = await res.json()
      if (data?.error) message = data.error
    } catch {
      /* 본문이 JSON이 아니면 기본 메시지 사용 */
    }
    throw new Error(message)
  }

  return res.status === 204 ? null : res.json()
}

// ---------- 화면에서 쓰는 함수 ----------

/** 규정 Q&A 챗봇 (U-01·U-02·U-03):
 *  { type: 'answer'|'procedure'|'clarify', answer, grounded, sources: [{ ref, regulation, article, revised_at, url }],
 *    procedure (type 이 procedure 일 때, getProcedure 응답과 같은 모양), options (type 이 clarify 일 때 업무 이름),
 *    contact (grounded 가 false 일 때 담당자: { department, name, phone }) }
 *  answer 안의 [1] 같은 번호는 sources[].ref 와 짝입니다. grounded 가 false 면 근거를 못 찾은 답변입니다. */
export function askQa(question) {
  if (USE_MOCK) return mock.askQa(question)
  return request('POST', '/api/qa', { question })
}

/** 업무절차·필요서류 안내 (U-02):
 *  { task, summary, documents: [{ name, detail, basis }], steps: [{ title, detail, basis }],
 *    deadline: { text, basis }, approver: { text, basis, check }, grounded, sources: [...] } */
export function getProcedure(task) {
  if (USE_MOCK) return mock.getProcedure(task)
  return request('POST', '/api/procedure', { task })
}

/** 청구 검증: { overall, items: [{ field, verdict, message, basis, fix }] } */
export function verifyClaim(claim) {
  if (USE_MOCK) return mock.verifyClaim(claim)
  return request('POST', '/api/verify', claim)
}

/** 내 체크리스트 목록: [{ id, task, summary, deadline, approver, sources, created_at,
 *    items: [{ id, kind: 'document'|'step', title, detail, basis, done, done_at }] }] */
export function getChecklists() {
  if (USE_MOCK) return mock.getChecklists()
  return request('GET', '/api/checklists')
}

/** 절차 안내를 내 체크리스트로 저장. task 는 안내 응답의 task 값입니다. */
export function createChecklist(task) {
  if (USE_MOCK) return mock.createChecklist(task)
  return request('POST', '/api/checklists', { task })
}

/** 체크 항목 완료 표시를 바꿉니다. 바뀐 항목을 돌려줍니다. */
export function updateChecklistItem(checklistId, itemId, done) {
  if (USE_MOCK) return mock.updateChecklistItem(checklistId, itemId, done)
  return request('PATCH', `/api/checklists/${checklistId}/items/${itemId}`, { done })
}

/** 내 체크리스트를 삭제합니다. */
export function deleteChecklist(checklistId) {
  if (USE_MOCK) return mock.deleteChecklist(checklistId)
  return request('DELETE', `/api/checklists/${checklistId}`)
}

/** 체크리스트: { type, items: [{ id, text, basis }] } */
export function getChecklist(type = '국내출장') {
  if (USE_MOCK) return mock.getChecklist(type)
  return request('GET', `/api/checklist?type=${encodeURIComponent(type)}`)
}

// ---------- 출장비 계산 (U-05) ----------

/**
 * 출장 정보 → 받을 수 있는 금액. 요청·응답 모양은 docs/API.md 3-5, docs/U-05_출장비계산.md.
 * 보내는 것: { trip_type, grade, trip: {...}, fares?: [{ type, amount, seat_class }], private_car?: {...} }
 * 받는 것:   { grade, region, days, nights, lines: [{ field, amount, type, formula, basis, note }],
 *             summary: { fixed_total, lodging_cap, transport_total, estimated_max }, notes: [], verify_request: {...} }
 * verify_request 를 그대로 verifyClaim() 에 넣으면 U-04 검증으로 이어집니다.
 */
export function calcTravel(req) {
  if (USE_MOCK) return mock.calcTravel(req)
  return request('POST', '/api/travel-calc', req)
}

// ---------- 정산 제출 (직원 → 관리자 검토 대기함) ----------

/** 검증을 마친 청구 내역을 제출(검토 요청). claim 은 verifyClaim 에 보낸 것과 같은 모양,
 *  extra: { purpose, account, verify_result }. 돌려주는 것은 관리자 목록 한 건과 같은 모양 (id 가 S-2026-00N). */
export function createSubmission(claim, extra = {}) {
  if (USE_MOCK) return mock.createSubmission(claim, extra)
  return request('POST', '/api/submissions', { ...claim, ...extra })
}

/** 내 제출 내역: { total, items: [...] } (로그인한 사번 기준) */
export function listMySubmissions() {
  if (USE_MOCK) return mock.listMySubmissions()
  return request('GET', '/api/submissions')
}

// ---------- 관리자 (M-01 정산 검토 대기함) ----------

/** 제출 건 목록: { total, items: [{ id, submitter, dept, type, purpose, amount, date, verdict, status, step, items[] }] } */
export function listSubmissions() {
  if (USE_MOCK) return mock.listSubmissions()
  return request('GET', '/api/admin/submissions')
}

/** 제출 건 상세 (목록 항목 + items 전체) */
export function getSubmission(id) {
  if (USE_MOCK) return mock.getSubmission(id)
  return request('GET', `/api/admin/submissions/${encodeURIComponent(id)}`)
}

/** 승인/반려 저장. decision: '승인' | '반려' */
export function decideSubmission(id, decision, message = '') {
  if (USE_MOCK) return mock.decideSubmission(id, decision, message)
  return request('POST', `/api/admin/submissions/${encodeURIComponent(id)}/decision`, { decision, message })
}

/** 반려 메시지 초안 (백엔드 RAG 생성): { message, sources[] }
 *  extraIssues: AI 판정 항목이 아닌 추가 사유 (예: M-05 계정과목 불일치). 모양은 items[] 한 개와 같습니다. */
export function draftRejectMessage(id, issueFields, extraIssues = []) {
  if (USE_MOCK) return mock.draftRejectMessage(id, issueFields, extraIssues)
  return request('POST', `/api/admin/submissions/${encodeURIComponent(id)}/reject-draft`, {
    issue_fields: issueFields,
    extra_issues: extraIssues,
  })
}

// ---------- 계정과목 검토 (M-05) ----------

/**
 * 제출 건 → U-07 결의서 초안 API 로 AI 계정과목 제안을 받아 한 줄로 정리합니다. 관리자 전용 API 추가 없음.
 * 받는 것: { account, sub_accounts: [], confidence: '규정 확인'|'가정', basis }
 * account 가 '담당자 확인' 이면 AI가 과목을 정하지 못한 것입니다.
 */
export async function suggestAccount(submission) {
  if (USE_MOCK) return mock.suggestAccount(submission)
  const draft = await request('POST', '/api/voucher-draft', toVoucherRequest(submission))
  return pickSuggestion(draft.lines ?? [])
}

/** 제출 건을 /api/voucher-draft 요청 모양으로 바꿉니다.
 *  국내출장은 AI 판정 항목(숙박비·식비·일비·교통비)을 그대로 항목으로, 그 외는 용도 1건을 항목으로 보냅니다. */
export function toVoucherRequest(sub) {
  const base = { trip_type: sub.type, requester: { name: sub.submitter, department: sub.dept } }
  if (sub.type === '국내출장') {
    const fields = [...new Set(sub.items.map((it) => it.field))].filter((f) => f !== '정산 기한')
    const items = fields.map((field, i) => ({ field, amount: i === 0 ? sub.amount : 0 }))
    return { ...base, items: items.length ? items : [{ field: sub.purpose, amount: sub.amount }] }
  }
  return { ...base, items: [{ field: sub.purpose, amount: sub.amount, date: sub.date, merchant: sub.merchant ?? '' }] }
}

/** 결의서 lines[] 중 금액이 가장 큰 과목을 대표로, 세목은 모두 모읍니다. */
export function pickSuggestion(lines) {
  if (!lines.length) return { account: '담당자 확인', sub_accounts: [], confidence: '가정', basis: '' }
  const top = [...lines].sort((a, b) => (b.amount ?? 0) - (a.amount ?? 0))[0]
  const sub_accounts = [...new Set(lines.filter((l) => l.account === top.account).map((l) => l.sub_account).filter(Boolean))]
  return { account: top.account, sub_accounts, confidence: top.confidence, basis: top.basis }
}

// 검토 상태 값 (백엔드 app/core/constants.py 와 동일)
export const STATUS = { PENDING: '검토 대기', APPROVED: '승인', REJECTED: '반려' }

// 직원이 결의서에 적는 계정과목 후보 (M-05 에서 AI 제안과 비교). 백엔드 voucher.py 의 과목명과 같게 유지
export const ACCOUNTS = ['여비교통비', '업무추진비', '조직관리비', '소모품비', '도서인쇄비', '통신비', '교육훈련비', '지급수수료', '차량유지비']

// ---------- 영수증 인식 (U-06 영수증 자동 정리) ----------

// 용도 후보 값 (experiments/receipt-ocr 의 PURPOSES 와 같아야 함)
export const PURPOSES = ['식비', '회의비', '교통비', '숙박비', '주유비', '소모품비', '도서비', '경조사비', '기타']

/**
 * 영수증 사진 1장 → 추출값.
 * 보내는 것: { filename, media_type, image_base64 }
 * 받는 것:   { merchant, business_type, date, time, total_amount, card_last4, approval_no,
 *             items: [{ name, amount }], purpose_candidates: [], confidence: 'high'|'medium'|'low', notes }
 * 사진에 없는 값은 null 로 옵니다.
 */
export function recognizeReceipt({ filename, mediaType, base64 }) {
  if (USE_MOCK) return mock.recognizeReceipt({ filename })
  return request('POST', '/api/receipt', { filename, media_type: mediaType, image_base64: base64 })
}
