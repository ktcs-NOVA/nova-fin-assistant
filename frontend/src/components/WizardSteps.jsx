// 단계별 화면(마법사) 위쪽의 진행 표시: ✓ 지난 단계 · 숫자 강조 = 지금 · 흐림 = 앞으로
// steps: 단계 이름 배열, current: 1부터 시작하는 현재 단계
//
// 관리자 검토처럼 단계를 건너뛸 수 있는 화면에서는 두 가지를 더 줍니다 (직원 화면은 안 줌 → 예전과 똑같이 동작).
//   onPick(n)  단계를 누르면 그 단계로 감
//   marks      단계별 결과 ['ok' | 'issue' | undefined, …] — 순서가 아니라 결과로 칠함: 문제 없음 ✓ · 확인할 것 있음 !

export default function WizardSteps({ steps, current, marks, onPick }) {
  return (
    <ol className={`wsteps${onPick ? ' pickable' : ''}`} aria-label={onPick ? '검토 단계' : '정산 단계'}>
      {steps.map((label, i) => {
        const n = i + 1
        const mark = marks?.[i]
        const state = n === current ? 'now'
          : marks ? (mark === 'issue' ? 'issue' : mark === 'ok' ? 'done' : 'todo')
          : n < current ? 'done' : 'todo'
        const inner = (
          <>
            <span className="wstep-no">{state === 'done' ? '✓' : state === 'issue' ? '!' : n}</span>
            <span className="wstep-label">{label}</span>
          </>
        )
        // 지금 단계라도 확인할 것이 있으면 표시를 남김
        const cls = state === 'now' && mark === 'issue' ? 'now has-issue' : state
        return (
          <li key={label} className={cls} aria-current={state === 'now' ? 'step' : undefined}>
            {onPick ? (
              <button type="button" className="wstep-btn" onClick={() => onPick(n)}
                aria-label={`${n}단계 ${label}${mark === 'issue' ? ' (확인할 것 있음)' : mark === 'ok' ? ' (문제 없음)' : ''}`}>
                {inner}
              </button>
            ) : inner}
          </li>
        )
      })}
    </ol>
  )
}
