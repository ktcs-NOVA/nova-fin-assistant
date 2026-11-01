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
