// 목업 모드: 백엔드 없이 JSON 파일을 돌려줍니다.
// 응답 모양은 docs/API.md 3번과 같습니다. 백엔드는 이 JSON과 같은 모양으로 응답하면 됩니다.
// 내용은 전부 "(예시)" 가짜 데이터이며, 실제 판정은 백엔드가 합니다.

import qaData from '../mocks/qa.json'
import qaUngroundedData from '../mocks/qa-ungrounded.json'
import procedureData from '../mocks/procedure.json'
import checklistData from '../mocks/checklist.json'
import receiptsData from '../mocks/receipts.json'

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

// ---------- 관리자 (M-01 정산 검토 대기함) ----------

import submissionsData from '../mocks/submissions.json'

// 메모리 안에서만 바뀌는 상태 (새로고침하면 초기화)
const submissions = structuredClone(submissionsData.items)

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
export async function draftRejectMessage(id, issueFields) {
  await wait(700)
  const found = submissions.find((s) => s.id === id)
  if (!found) throw new Error(`제출 건 ${id} 을(를) 찾을 수 없습니다.`)
  const picked = found.items.filter((it) => issueFields.includes(it.field))
  if (!picked.length) throw new Error('반려 사유를 하나 이상 선택해 주세요.')
  const lines = picked.map(
    (it, i) => `${i + 1}. [${it.field}] ${it.message}\n   - 근거: ${it.basis}\n   - 수정: ${it.fix || '담당자와 협의'}`,
  )
  return {
    message: `${found.submitter}님, 제출하신 ${found.purpose} 정산 건은 아래 사유로 반려되었습니다.\n\n${lines.join('\n')}\n\n수정 후 다시 제출해 주세요.`,
    sources: picked.map((it) => it.basis),
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
