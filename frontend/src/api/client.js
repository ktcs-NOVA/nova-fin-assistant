// API 호출 모듈. 모든 화면은 이 파일의 함수만 사용합니다.
//
//   VITE_API_BASE  백엔드 주소 (기본 http://localhost:8000)
//   VITE_USE_MOCK  "true"면 백엔드 대신 src/mocks/*.json 사용
//
// 설정은 frontend/.env (공통) 또는 frontend/.env.local (내 PC 전용) 에 적습니다.

import * as mock from './mock.js'

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
    res = await fetch(API_BASE + path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
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
 *    procedure (type 이 procedure 일 때, getProcedure 응답과 같은 모양), options (type 이 clarify 일 때 업무 이름) }
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
