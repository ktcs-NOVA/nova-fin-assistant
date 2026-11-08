// 지출 건 처리 단계 표시 (PM 흐름 문서의 6단계)
// current: 1~6. 지난 단계는 완료, 현재는 강조, 이후는 흐리게.

const STEPS = ['지출 건 생성', '규정 검증', '계정과목 추천', '결의서 초안', '관리자 검토', '예산 반영']

export default function Stepper({ current = 1 }) {
  return (
    <ol className="stepper" aria-label="처리 단계">
      {STEPS.map((label, i) => {
        const n = i + 1
        const state = n < current ? 'done' : n === current ? 'now' : 'todo'
        return (
          <li key={label} className={state} aria-current={state === 'now' ? 'step' : undefined}>
            <span className="step-no">{n}</span>
            <span className="step-label">{label}</span>
          </li>
        )
      })}
    </ol>
  )
}
