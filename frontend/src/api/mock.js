// 목업 모드: 백엔드 없이 JSON 파일을 돌려줍니다.
// 응답 모양은 docs/API.md 3번과 같습니다. 백엔드는 이 JSON과 같은 모양으로 응답하면 됩니다.
// 내용은 전부 "(예시)" 가짜 데이터이며, 실제 판정은 백엔드가 합니다.

import verifyData from '../mocks/verify.json'
import qaData from '../mocks/qa.json'
import checklistData from '../mocks/checklist.json'

// 실제 서버처럼 잠깐 기다렸다가 응답 (로딩 표시를 테스트하기 위해)
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export async function askQa(question) {
  await wait(600)
  if (!question?.trim()) throw new Error('질문을 입력해 주세요.')
  return qaData
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
