// 정산 화면 오른쪽 아래에 떠 있는 NOVA 마스코트. 누르면 그 자리에서 규정을 묻고 답을 받는 작은 창이 열립니다.
// 화면을 옮겨도(출장 정산 → 검증 → 제출) 대화가 이어지도록 Layout 에 한 번만 붙여 둡니다.
// 답변은 규정 물어보기 화면과 같은 askQa / QaReply 를 씁니다.

import { useEffect, useRef, useState } from 'react'
import { askQa } from '../api/client.js'
import QaReply from './QaReply.jsx'
import mascot from '../assets/nova-mascot.png'

// 지금 보는 화면에 맞는 예시 질문
const EXAMPLES = {
  travel: ['부산 1박 출장 숙박비 상한은?', '자가용으로 출장 가면 어떻게 정산해요?', '출장 다녀오면 뭘 준비해야 해?'],
  receipt: ['밤 11시 넘어서 법인카드를 써도 돼요?', '회의비는 참석자를 꼭 적어야 해요?', '법인카드 쓰고 나서 해야 할 일은?'],
  verify: ['숙박비에 조식이 포함돼 있으면 식비는?', '회의비는 참석자를 꼭 적어야 해요?', '보완 필요가 나오면 어떻게 해요?'],
  default: ['출장 다녀오면 뭘 준비해야 해?', '법인카드 쓰고 나서 해야 할 일은?'],
}

let nextId = 1

export default function AskDock({ page }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])   // { id, text, status: 'loading'|'done'|'error', result, error }
  const [input, setInput] = useState('')
  const bodyEndRef = useRef(null)
  const inputRef = useRef(null)
  const busy = messages.some((m) => m.status === 'loading')

  useEffect(() => { bodyEndRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' }) }, [messages, open])
  useEffect(() => { if (open) inputRef.current?.focus() }, [open])

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
    if (e.key === 'Escape') { setOpen(false); return }
    // Enter 로 보내기, Shift+Enter 는 줄바꿈. 한글 조합 중인 Enter 는 무시 (두 번 전송 방지)
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      send(input)
    }
  }

  if (!open) {
    return (
      <button type="button" className="ask-fab" onClick={() => setOpen(true)} aria-label="NOVA에게 규정 물어보기">
        <span className="ask-fab-tip">규정 물어보세요!</span>
        <img src={mascot} alt="" />
      </button>
    )
  }

  const chips = EXAMPLES[page] ?? EXAMPLES.default
  return (
    <section className="ask-panel" role="dialog" aria-label="규정 물어보기" onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false) }}>
      <header className="ask-head">
        <img src={mascot} alt="" />
        <div className="ask-head-text">
          <b>NOVA에게 물어보기</b>
          <span>규정은 근거 조항과 함께 답해요</span>
        </div>
        {messages.length > 0 && (
          <button type="button" className="ask-head-btn" onClick={() => setMessages([])} disabled={busy}>새 대화</button>
        )}
        <button type="button" className="ask-head-btn" onClick={() => setOpen(false)} aria-label="질문창 닫기">닫기</button>
      </header>

      <div className="ask-body">
        {messages.length === 0 && (
          <div className="ask-empty">
            <p>정산하다가 궁금한 규정이 있으면 바로 물어보세요.</p>
            <div className="chips">
              {chips.map((q) => (
                <button key={q} type="button" className="chip" onClick={() => send(q)}>{q}</button>
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
              {m.status === 'done' && <QaReply result={m.result} onAsk={send} />}
            </div>
          </div>
        ))}
        <div ref={bodyEndRef} />
      </div>

      <form className="ask-form" onSubmit={(e) => { e.preventDefault(); send(input) }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="예) 숙박비 한도는 얼마야?"
          rows={2}
          maxLength={1000}
          aria-label="질문 입력"
        />
        <button type="submit" className="btn primary" disabled={busy || !input.trim()}>{busy ? '답변 중…' : '보내기'}</button>
      </form>
    </section>
  )
}
