// 규정 Q&A 화면 (U-01 규정 통합 Q&A · U-02 업무절차 안내 · U-03 근거·출처 표시)
// 위쪽 전환 버튼으로 "규정 질문"과 "업무 절차 안내"를 고르고, 대화처럼 묻고 답합니다.
// 모든 답변에는 근거 조항이 붙고, 근거가 없으면 "담당자 확인 필요"로 표시됩니다.

import { useEffect, useRef, useState } from 'react'
import { askQa, getProcedure } from '../api/client.js'
import QaAnswer from '../components/QaAnswer.jsx'
import ProcedureGuide from '../components/ProcedureGuide.jsx'

// 모드별 설정. 예시 질문을 바꾸려면 examples 만 고치면 됩니다.
const MODES = {
  qa: {
    label: '규정 질문',
    request: askQa,
    Answer: QaAnswer,
    placeholder: '규정에 대해 물어보세요. 예) 출장 때 자가용 쓰면 비용은 어떻게 돼요?',
    loading: '관련 조항을 찾는 중…',
    examples: [
      '출장 때 자가용 쓰면 비용은 어떻게 돼요?',
      '숙박비에 조식이 포함돼 있으면 식비는?',
      '밤 11시 넘어서 법인카드를 써도 돼요?',
      '업무추진비 50만원 넘게 쓰려면 뭐 해야 돼요?',
    ],
  },
  procedure: {
    label: '업무 절차 안내',
    request: getProcedure,
    Answer: ProcedureGuide,
    placeholder: '처음 하는 업무를 적어 주세요. 예) 국내 출장비 정산하려면?',
    loading: '필요 서류와 절차를 정리하는 중…',
    examples: ['국내 출장비 정산하려면?', '법인카드 쓰고 나서 처리할 일은?', '업무추진비 집행 절차는?'],
  },
}

let nextId = 1

export default function QaPage() {
  const [mode, setMode] = useState('qa')
  const [messages, setMessages] = useState([]) // { id, mode, text, status: 'loading'|'done'|'error', result, error }
  const [input, setInput] = useState('')
  const endRef = useRef(null)

  const busy = messages.some((m) => m.status === 'loading')
  const config = MODES[mode]

  // 새 메시지가 생기면 맨 아래로 스크롤
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  async function send(text) {
    const question = text.trim()
    if (!question || busy) return

    const id = nextId++
    const current = mode
    setInput('')
    setMessages((prev) => [...prev, { id, mode: current, text: question, status: 'loading' }])

    try {
      const result = await MODES[current].request(question)
      setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, status: 'done', result } : m)))
    } catch (e) {
      setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, status: 'error', error: e.message } : m)))
    }
  }

  function onKeyDown(e) {
    // Enter 로 보내기, Shift+Enter 는 줄바꿈. 한글 조합 중인 Enter 는 무시 (두 번 전송 방지)
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      send(input)
    }
  }

  return (
    <section className="qa">
      <div className="page-title">
        <h1>규정 Q&A</h1>
        <span className="desc">경비 규정에 대해 질문하면 근거 조항과 함께 답합니다.</span>
      </div>

      <div className="qa-toolbar">
        <div className="segmented" role="tablist" aria-label="질문 종류">
          {Object.entries(MODES).map(([id, m]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={mode === id}
              className={mode === id ? 'on' : ''}
              onClick={() => setMode(id)}
            >
              {m.label}
            </button>
          ))}
        </div>
        {messages.length > 0 && (
          <button type="button" className="btn small" onClick={() => setMessages([])} disabled={busy}>
            새 대화
          </button>
        )}
      </div>

      <div className="chat">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>{mode === 'qa' ? '이런 질문을 해보세요' : '이런 업무를 안내받을 수 있어요'}</p>
            <div className="chips">
              {config.examples.map((q) => (
                <button key={q} type="button" className="chip" onClick={() => send(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => {
          const { Answer, loading, label } = MODES[m.mode]
          return (
            <div key={m.id} className="turn">
              <div className="bubble-user">
                {m.mode === 'procedure' && <span className="bubble-tag">{label}</span>}
                {m.text}
              </div>
              <div className="bubble-bot">
                {m.status === 'loading' && <p className="loading">{loading}</p>}
                {m.status === 'error' && <div className="error">{m.error}</div>}
                {m.status === 'done' && <Answer result={m.result} />}
              </div>
            </div>
          )
        })}
        <div ref={endRef} />
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault()
          send(input)
        }}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={config.placeholder}
          rows={2}
          maxLength={1000}
          aria-label="질문 입력"
        />
        <button type="submit" className="btn primary" disabled={busy || !input.trim()}>
          {busy ? '답변 중…' : '보내기'}
        </button>
      </form>
      <p className="hint disclaimer">
        AI가 등록된 규정을 근거로 답합니다. 최종 판단은 근거 조항 원문과 담당자 확인을 따르세요.
      </p>
    </section>
  )
}
