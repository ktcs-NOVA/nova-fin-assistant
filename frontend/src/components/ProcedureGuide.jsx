// 업무절차·필요서류 안내 카드 (U-02)
// Q&A 가 "질문에 답"이라면, 이 카드는 "해야 할 일 목록"입니다.
// ① 필요 서류 ② 작성 순서 ③ 제출 기한 ④ 결재자 를 근거 조항과 함께 보여줍니다.
// 데이터 모양은 docs/API.md 3-4 의 응답과 같습니다.

import { useState } from 'react'
import { VERDICT, createChecklist } from '../api/client.js'
import GroundNotice from './GroundNotice.jsx'
import SourceList from './SourceList.jsx'

function Basis({ text }) {
  return text ? <span className="basis">근거 · {text}</span> : null
}

// 이 안내를 내 체크리스트로 저장합니다. 두 번 저장되지 않도록 저장 후에는 이동 버튼으로 바뀝니다.
function SaveChecklist({ task, onNavigate }) {
  const [status, setStatus] = useState('idle') // idle | saving | saved
  const [error, setError] = useState('')

  async function save() {
    setStatus('saving')
    setError('')
    try {
      await createChecklist(task)
      setStatus('saved')
    } catch (e) {
      setError(e.message)
      setStatus('idle')
    }
  }

  return (
    <div className="save-checklist">
      {status === 'saved' ? (
        <>
          <span className="badge good" role="status">저장했습니다</span>
          <button type="button" className="btn small" onClick={() => onNavigate?.('checklist')}>
            체크리스트 보기
          </button>
        </>
      ) : (
        <button type="button" className="btn small primary" onClick={save} disabled={status === 'saving'}>
          {status === 'saving' ? '저장 중…' : '내 체크리스트에 저장'}
        </button>
      )}
      {error && <span className="save-error" role="alert">{error}</span>}
    </div>
  )
}

export default function ProcedureGuide({ result, onNavigate }) {
  const { task, summary, documents = [], steps = [], deadline, approver, sources = [] } = result
  const grounded = result.grounded ?? sources.length > 0

  return (
    <div className="answer">
      <div className="answer-head">
        {task && <h3 className="procedure-task">{task}</h3>}
        <GroundNotice grounded={grounded} count={sources.length} />
      </div>
      {summary && <p className="answer-text">{summary}</p>}

      {grounded && (
        <div className="procedure">
          <section>
            <h4><span className="num">1</span>필요 서류</h4>
            <ul className="check-list">
              {documents.map((d) => (
                <li key={d.name}>
                  <strong>{d.name}</strong>
                  {d.detail && <span className="detail">{d.detail}</span>}
                  <Basis text={d.basis} />
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h4><span className="num">2</span>작성 순서</h4>
            <ol className="step-list">
              {steps.map((s) => (
                <li key={s.title}>
                  <strong>{s.title}</strong>
                  {s.detail && <span className="detail">{s.detail}</span>}
                  <Basis text={s.basis} />
                </li>
              ))}
            </ol>
          </section>

          {deadline && (
            <section>
              <h4>
                <span className="num">3</span>제출 기한
                {deadline.check && <span className="badge warn">{VERDICT.CHECK}</span>}
              </h4>
              <p className="fact">{deadline.text}</p>
              <Basis text={deadline.basis} />
            </section>
          )}

          {approver && (
            <section>
              <h4>
                <span className="num">4</span>결재자
                {approver.check && <span className="badge warn">{VERDICT.CHECK}</span>}
              </h4>
              <p className="fact">{approver.text}</p>
              <Basis text={approver.basis} />
            </section>
          )}
        </div>
      )}

      <SourceList sources={sources} />
      {grounded && <SaveChecklist task={task} onNavigate={onNavigate} />}
    </div>
  )
}
