// "확인 필요"를 종류별로 걸러 보는 단추 줄: 보완 필요 · 담당자 확인 · 계정과목 · 반려 (건수 포함).
// 관리자 홈에서는 누르면 그 종류만 걸러진 검토 대기함으로 가고, 대기함에서는 그 자리에서 걸러집니다.
// counts 는 pages/admin/reviewQueue.js 의 countQueue 결과, active 는 지금 고른 종류.

import { KINDS } from '../pages/admin/reviewQueue.js'

export default function NeedsKinds({ counts, active, onPick }) {
  if (!counts) return null
  return (
    <div className="kind-row" role="group" aria-label="확인 필요 종류별로 보기">
      <span className="hint">종류별로 보기</span>
      {KINDS.map((k) => (
        <button key={k.id} type="button" className={`kind-chip${active === k.id ? ' on' : ''}`} aria-pressed={active === k.id}
          disabled={!counts[k.id]} onClick={() => onPick(active === k.id ? null : k.id)}>
          {k.label} <b>{counts[k.id]}</b>
        </button>
      ))}
    </div>
  )
}
