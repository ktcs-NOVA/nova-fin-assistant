// 정산 건의 증빙 서류 상태를 한 칸으로: "서류 2/2" (다 옴) · "서류 1/2" (일부) · "서류 미제출".
// docs 는 제출 건 응답의 { expected: [받아야 할 종류], sent: [받은 종류], missing: [안 온 종류] } 입니다 (백엔드 doc_status).
// 직원이 "관리자에게 보내기"까지 마친 서류만 받은 것으로 셉니다.

const LABEL = { 지출결과서: '지출 결과서' }

export default function DocsBadge({ docs }) {
  if (!docs?.expected?.length) return null   // 목업처럼 서류 상태가 없는 응답
  const total = docs.expected.length
  const got = total - docs.missing.length
  const tone = got === total ? 'good' : got > 0 ? 'warn' : 'muted'
  const names = (list) => list.map((k) => LABEL[k] ?? k).join(', ')
  const title = docs.missing.length ? `아직 안 온 서류: ${names(docs.missing)}` : `받은 서류: ${names(docs.expected)}`
  return <span className={`badge ${tone} docs-badge`} title={title}>{got === 0 ? '서류 미제출' : `서류 ${got}/${total}`}</span>
}
