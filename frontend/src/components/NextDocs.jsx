// "이어서 서류 쓰기": 정산에서 입력한 값으로 채운 서류 작성 화면(문서 작업)으로 넘어가는 버튼들.
// src 는 청구 검증 요청이나 제출 건. 이어 쓸 서류가 없는 유형이면 아무것도 그리지 않습니다.

import { docsForClaim } from '../utils/claimToDocs.js'

export default function NextDocs({ src, user, onNavigate, compact = false }) {
  const docs = docsForClaim(src, user)
  if (!docs.length || !onNavigate) return null
  const open = (d) => onNavigate('checklist', { newDoc: { kind: d.kind, fields: d.fields, origin: d.origin } })

  if (compact) {
    return (
      <span className="next-docs compact">
        {docs.map((d) => <button key={d.kind} type="button" className="link-btn" onClick={() => open(d)}>{d.label} →</button>)}
      </span>
    )
  }
  return (
    <div className="next-docs">
      <b>다음 단계 · 증빙 서류</b>
      <p className="hint">방금 입력한 날짜·금액·참석자를 그대로 채워 드려요. 빈 칸만 적으면 초안을 만들 수 있어요.</p>
      <div className="btn-row start">
        {docs.map((d) => <button key={d.kind} type="button" className="btn primary" onClick={() => open(d)}>{d.label} →</button>)}
      </div>
    </div>
  )
}
