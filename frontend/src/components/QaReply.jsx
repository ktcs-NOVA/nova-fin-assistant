// 규정 Q&A 답변 한 건을 그리는 부분: 규정 답변 / 절차 안내 / 되묻기
// 규정 물어보기 화면(QaPage)과 정산 화면의 떠 있는 질문창(AskDock)이 함께 씁니다.

import QaAnswer from './QaAnswer.jsx'
import ProcedureGuide from './ProcedureGuide.jsx'

function Clarify({ result, onPick }) {
  return (
    <div className="answer">
      <p className="answer-text">{result.answer}</p>
      <div className="chips clarify-options">
        {result.options.map((task) => (
          <button key={task} type="button" className="chip" onClick={() => onPick(`${task} 절차 알려줘`)}>
            {task}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function QaReply({ result, onAsk }) {
  if (result.type === 'procedure' && result.procedure) {
    return <ProcedureGuide result={result.procedure} />
  }
  if (result.type === 'clarify') return <Clarify result={result} onPick={onAsk} />
  return <QaAnswer result={result} />
}
