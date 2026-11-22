// 규정 확인하기: 규정 원문 보기(RegulationViewer) + 규정 Q&A 챗봇 (U-01 규정 답변 · U-02 업무절차 안내 · U-03 근거 표시)
// 위쪽 토글로 둘을 오갑니다. 처음에는 원문 보기, 질문을 들고 넘어오면(param.ask) 챗봇이 열립니다.
// 답변의 근거 조항에서 "원문에서 보기"를 누르면 원문 보기에서 그 조항이 펼쳐집니다.
// 입력창은 하나입니다. 백엔드가 질문을 보고 답하는 방식을 고르고, 응답의 type 으로 화면을 정합니다.
//   answer    규정 답변 + 근거 조항
//   procedure 절차 안내 카드
//   clarify   어떤 업무인지 되묻기 + 업무 버튼

import { useEffect, useRef, useState } from 'react'
import { askQa } from '../api/client.js'
import QaReply from '../components/QaReply.jsx'
import NovaSay from '../components/NovaSay.jsx'
import RegulationViewer from '../components/RegulationViewer.jsx'

// 예시 질문. 규정 질문과 절차 질문을 섞어 두면 챗봇이 알아서 고르는 모습을 볼 수 있습니다.
const EXAMPLES = [
  '출장 다녀오면 뭘 준비해야 해?',
  '숙박비에 조식이 포함돼 있으면 식비는?',
  '법인카드 쓰고 나서 해야 할 일은?',
  '밤 11시 넘어서 법인카드를 써도 돼요?',
]

let nextId = 1

export default function QaPage({ param }) {
  const [messages, setMessages] = useState([]) // { id, text, status: 'loading'|'done'|'error', result, error }
  const [input, setInput] = useState('')
  const [tab, setTab] = useState(param?.ask || param?.tab === 'ask' ? 'ask' : 'read')   // read: 원문 보기 / ask: 챗봇
  const [focus, setFocus] = useState(null)   // 원문에서 펼쳐 볼 조항 { regulation, article, n }
  const jumps = useRef(0)
  const endRef = useRef(null)
  const askedRef = useRef(false)   // 홈 검색바에서 넘어온 질문은 한 번만 보냄 (개발 모드 이중 실행 방지)

  const busy = messages.some((m) => m.status === 'loading')

  // 새 메시지가 생기면 맨 아래로 스크롤
  useEffect(() => {
    if (messages.length) endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  function openSource(source) {
    jumps.current += 1   // 넘어올 때마다 원문 화면을 새로 열어, 하던 찾기를 지우고 그 조항을 보여 줌
    setFocus({ regulation: source.regulation, article: source.article, n: jumps.current })
    setTab('read')
  }

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

  useEffect(() => {
    if (param?.ask && !askedRef.current) {
      askedRef.current = true
      send(param.ask)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
        <h1>규정 확인하기</h1>
        <span className="desc">규정 원문을 바로 읽거나, 궁금한 점을 NOVA에게 물어보세요.</span>
      </div>

      <div className="seg qa-tabs" role="tablist">
        <button type="button" role="tab" aria-selected={tab === 'read'} className={tab === 'read' ? 'on' : ''} onClick={() => setTab('read')}>규정 원문 보기</button>
        <button type="button" role="tab" aria-selected={tab === 'ask'} className={tab === 'ask' ? 'on' : ''} onClick={() => setTab('ask')}>NOVA에게 물어보기</button>
      </div>

      {/* 두 화면을 모두 그려 두고 하나만 보여 줌: 오가도 대화와 읽던 위치가 남음 */}
      <div hidden={tab !== 'read'}>
        <RegulationViewer key={focus?.n ?? 0} focus={focus} />
      </div>

      <div hidden={tab !== 'ask'}>

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
            <NovaSay>
              <p className="answer-text">안녕하세요, NOVA예요! 규정이 궁금하면 근거 조항과 함께 답해 드리고, 처리 절차를 물으면 단계별로 안내해 드려요.</p>
            </NovaSay>
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
            <NovaSay loading={m.status === 'loading'}>
              {m.status === 'error' && <div className="error">{m.error}</div>}
              {m.status === 'done' && <QaReply result={m.result} onAsk={send} onOpenSource={openSource} />}
            </NovaSay>
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
      </div>
    </section>
  )
}
