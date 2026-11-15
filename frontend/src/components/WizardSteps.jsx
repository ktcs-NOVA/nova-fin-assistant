// 단계별 화면(마법사) 위쪽의 진행 표시: ✓ 지난 단계 · 숫자 강조 = 지금 · 흐림 = 앞으로
// steps: 단계 이름 배열, current: 1부터 시작하는 현재 단계

export default function WizardSteps({ steps, current }) {
  return (
    <ol className="wsteps" aria-label="정산 단계">
      {steps.map((label, i) => {
        const n = i + 1
        const state = n < current ? 'done' : n === current ? 'now' : 'todo'
        return (
          <li key={label} className={state} aria-current={state === 'now' ? 'step' : undefined}>
            <span className="wstep-no">{state === 'done' ? '✓' : n}</span>
            <span className="wstep-label">{label}</span>
          </li>
        )
      })}
    </ol>
  )
}
