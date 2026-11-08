// 목업 모드: 백엔드 없이 JSON 파일을 돌려줍니다.
// 응답 모양은 docs/API.md 3번과 같습니다. 백엔드는 이 JSON과 같은 모양으로 응답하면 됩니다.
// 내용은 전부 "(예시)" 가짜 데이터이며, 실제 판정은 백엔드가 합니다.

import verifyData from '../mocks/verify.json'
import qaData from '../mocks/qa.json'
import qaUngroundedData from '../mocks/qa-ungrounded.json'
import procedureData from '../mocks/procedure.json'
import checklistData from '../mocks/checklist.json'

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

export async function verifyClaim(claim) {
  await wait(800)
  if (!claim?.items?.length) throw new Error('청구 항목이 비어 있습니다.')
  return verifyData
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
