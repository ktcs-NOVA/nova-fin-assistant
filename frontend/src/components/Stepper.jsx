// 지출 건 처리 단계 표시 (PM 흐름 문서의 6단계)
// current: 1~6. 지난 단계는 완료, 현재는 강조, 이후는 흐리게.
// status 가 반려면 5단계(관리자 검토)에서 끝난 것으로 표시하고 6단계 예산 반영은 진행하지 않음으로 흐리게 둡니다.
// 승인이면 6단계까지 모두 완료로 표시합니다.

import { STATUS } from '../api/client.js'

const STEPS = ['지출 건 생성', '규정 검증', '계정과목 추천', '결의서 초안', '관리자 검토', '예산 반영']
const ADMIN_STEP = 5

export default function Stepper({ current = 1, status }) {
  const rejected = status === STATUS.REJECTED
  const approved = status === STATUS.APPROVED

  return (
    <ol className="stepper" aria-label="처리 단계">
      {STEPS.map((label, i) => {
        const n = i + 1
        let state
        if (rejected) state = n < ADMIN_STEP ? 'done' : n === ADMIN_STEP ? 'now rejected' : 'skip'
        else if (approved) state = 'done'
        else state = n < current ? 'done' : n === current ? 'now' : 'todo'
        const text = rejected && n === ADMIN_STEP ? `${label} · 반려` : rejected && n > ADMIN_STEP ? `${label} (진행 안 함)` : label
        return (
          <li key={label} className={state} aria-current={state.startsWith('now') ? 'step' : undefined}>
            <span className="step-no">{n}</span>
            <span className="step-label">{text}</span>
          </li>
        )
      })}
    </ol>
  )
}
