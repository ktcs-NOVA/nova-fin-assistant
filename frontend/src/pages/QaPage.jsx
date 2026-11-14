// 규정 Q&A 챗봇 (U-01 규정 답변 · U-02 업무절차 안내 · U-03 근거 표시)
// 입력창은 하나입니다. 백엔드가 질문을 보고 답하는 방식을 고르고, 응답의 type 으로 화면을 정합니다.
//   answer    규정 답변 + 근거 조항
//   procedure 절차 안내 카드
//   clarify   어떤 업무인지 되묻기 + 업무 버튼

import { useEffect, useRef, useState } from 'react'
import { askQa } from '../api/client.js'
import QaAnswer from '../components/QaAnswer.jsx'
import ProcedureGuide from '../components/ProcedureGuide.jsx'

// 예시 질문. 규정 질문과 절차 질문을 섞어 두면 챗봇이 알아서 고르는 모습을 볼 수 있습니다.
const EXAMPLES = [
  '출장 다녀오면 뭘 준비해야 해?',
  '숙박비에 조식이 포함돼 있으면 식비는?',
  '법인카드 쓰고 나서 해야 할 일은?',
  '밤 11시 넘어서 법인카드를 써도 돼요?',
]

let nextId = 1

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

function Reply({ result, onAsk }) {
  if (result.type === 'procedure' && result.procedure) {
    return <ProcedureGuide result={result.procedure} />
  }
  if (result.type === 'clarify') return <Clarify result={result} onPick={onAsk} />
  return <QaAnswer result={result} />
}

export default function QaPage() {
  const [messages, setMessages] = useState([]) // { id, text, status: 'loading'|'done'|'error', result, error }
  const [input, setInput] = useState('')
  const endRef = useRef(null)

  const busy = messages.some((m) => m.status === 'loading')

  // 새 메시지가 생기면 맨 아래로 스크롤
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  async function send(text) {
    const question = text.trim()
    if (!question || busy) return

    const id = nextId++
    setInput('')
    setMessages((prev) => [...prev, { id, text: question, status: 'loading' }])

    try {
      const result = await askQa(question)
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
        <span className="desc">규정이 궁금하거나 업무를 어떻게 처리할지 모를 때 물어보세요.</span>
      </div>

      {messages.length > 0 && (
        <div className="qa-toolbar">
          <button type="button" className="btn small" onClick={() => setMessages([])} disabled={busy}>
            새 대화
          </button>
        </div>
      )}

      <div className="chat">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>규정 내용은 근거 조항과 함께 답하고, 처리 절차를 물으면 단계별로 안내해요.</p>
            <div className="chips">
              {EXAMPLES.map((q) => (
                <button key={q} type="button" className="chip" onClick={() => send(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className="turn">
            <div className="bubble-user">{m.text}</div>
            <div className="bubble-bot">
              {m.status === 'loading' && <p className="loading">답변을 준비하는 중…</p>}
              {m.status === 'error' && <div className="error">{m.error}</div>}
              {m.status === 'done' && <Reply result={m.result} onAsk={send} />}
            </div>
          </div>
        ))}
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
          placeholder="예) 출장 다녀오면 뭘 준비해야 해? · 숙박비 한도는 얼마야?"
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
