// 규정 Q&A 답변 카드 (U-01 · U-03)
// 데이터 모양은 docs/API.md 3-1 의 응답과 같습니다: { answer, grounded, sources[] }
// 본문의 [1] 같은 인용 번호를 버튼으로 바꿔, 누르면 아래 출처 목록의 같은 번호가 강조됩니다.
// 인용 번호나 근거 조항에 마우스를 올리면(휴대폰은 탭) 조항 본문·별표를 작은 창으로 보여 줍니다.

import { useEffect, useRef, useState } from 'react'
import GroundNotice from './GroundNotice.jsx'
import SourceList from './SourceList.jsx'
import SourcePeek from './SourcePeek.jsx'

const OPEN_DELAY = 120 // 마우스가 스쳐 지나갈 때는 열지 않도록
const CLOSE_DELAY = 200 // 미리보기 창으로 마우스를 옮길 시간
const PEEK_WIDTH = 560
const PEEK_HEIGHT = 420 // 미리보기 창의 최대 높이 (머리 + 본문 320px) — 위/아래 자리 판단용

// '**교통비**' → <strong>교통비</strong> (AI 가 가끔 마크다운 굵은 글씨를 씀)
function rich(text, key) {
  if (!text.includes('**')) return text
  return text.split(/\*\*(.+?)\*\*/g).map((part, i) => (i % 2 ? <strong key={`${key}-${i}`}>{part}</strong> : part))
}

// "…지급합니다[1]." → ['…', <묶음: '지급합니다' + 인용 버튼 1>, '.']
// 인용 번호가 앞 단어와 다른 줄로 떨어지지 않도록 마지막 단어와 함께 묶습니다.
function withCitations(text, refs, activeRef, citeProps) {
  const out = []
  text.split(/(\[\d+\])/g).forEach((part, i) => {
    const m = part.match(/^\[(\d+)\]$/)
    if (!m) {
      out.push(part)
      return
    }
    const ref = Number(m[1])
    if (!refs.has(ref)) return // 출처 목록에 없는 번호는 표시하지 않음
    const cite = (
      <button
        key={`c${i}`}
        type="button"
        className={`cite ${activeRef === ref ? 'on' : ''}`}
        aria-label={`근거 ${ref}번 보기`}
        aria-haspopup="dialog"
        {...citeProps(ref)}
      >
        {ref}
      </button>
    )
    const prev = out.at(-1)
    const word = typeof prev === 'string' ? prev.match(/^([\s\S]*?)(\S+)$/) : null
    if (word) {
      out[out.length - 1] = word[1]
      out.push(
        <span key={`w${i}`} className="cite-wrap">
          {rich(word[2], `w${i}`)}
          {cite}
        </span>,
      )
    } else {
      out.push(cite)
    }
  })
  return out.map((part, i) => (typeof part === 'string' ? rich(part, `t${i}`) : part))
}

export default function QaAnswer({ result, onOpenSource }) {
  const [activeRef, setActiveRef] = useState(null)
  const [peek, setPeek] = useState(null) // { ref, top, left, width, pinned }
  const boxRef = useRef(null)
  const timer = useRef(null)
  const { answer = '', sources = [] } = result
  const grounded = result.grounded ?? sources.length > 0
  const refs = new Set(sources.map((s, i) => s.ref ?? i + 1))
  const byRef = new Map(sources.map((s, i) => [s.ref ?? i + 1, { ...s, ref: s.ref ?? i + 1 }]))

  const cancel = () => clearTimeout(timer.current)

  // 누른(가리킨) 요소 바로 아래, 답변 카드 안에 들어가도록 자리를 잡습니다.
  function place(ref, el, pinned) {
    const box = boxRef.current
    if (!box || !el || !byRef.get(ref)?.excerpt) return
    const b = box.getBoundingClientRect()
    const r = el.getBoundingClientRect()
    const width = Math.min(PEEK_WIDTH, b.width)
    const left = Math.max(0, Math.min(r.left - b.left, b.width - width))
    // 아래 공간이 모자라면(화면 아래쪽 근거 목록, 입력창에 가려짐) 위로 엽니다
    const above = window.innerHeight - r.bottom < PEEK_HEIGHT && r.top > PEEK_HEIGHT
    const top = above ? r.top - b.top - 6 : r.bottom - b.top + 6
    setPeek({ ref, top, left, width, above, pinned })
  }

  const hoverOpen = (ref, el) => {
    cancel()
    timer.current = setTimeout(() => place(ref, el, false), OPEN_DELAY)
  }
  const hoverClose = () => {
    cancel()
    timer.current = setTimeout(() => setPeek((p) => (p?.pinned ? p : null)), CLOSE_DELAY)
  }
  // 클릭·탭: 출처 강조 + 미리보기 고정 (한 번 더 누르면 닫힘)
  const toggle = (ref, el) => {
    cancel()
    setActiveRef(ref)
    if (peek?.ref === ref && peek.pinned) setPeek(null)
    else place(ref, el, true)
  }

  const citeProps = (ref) => ({
    onClick: (e) => toggle(ref, e.currentTarget),
    onMouseEnter: (e) => hoverOpen(ref, e.currentTarget),
    onMouseLeave: hoverClose,
    onFocus: (e) => place(ref, e.currentTarget, false),
    onBlur: hoverClose,
  })

  // 고정된 미리보기는 카드 밖을 누르거나 Esc 로 닫습니다.
  useEffect(() => {
    if (!peek) return undefined
    const onDown = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setPeek(null)
    }
    const onKey = (e) => {
      if (e.key === 'Escape') setPeek(null)
    }
    const onResize = () => setPeek(null) // 화면 크기가 바뀌면 자리가 어긋나므로 닫음
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    window.addEventListener('resize', onResize)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
      window.removeEventListener('resize', onResize)
    }
  }, [peek])

  useEffect(() => () => clearTimeout(timer.current), [])

  const peekSource = peek && byRef.get(peek.ref)

  return (
    <div className="answer" ref={boxRef}>
      <div className="answer-head">
        <GroundNotice grounded={grounded} count={sources.length} contact={result.contact} />
      </div>
      <p className="answer-text">{withCitations(answer, refs, activeRef, citeProps)}</p>
      {!grounded && (
        <p className="answer-hint">질문에 직급이나 출장 지역처럼 구체적인 조건을 함께 적어 다시 물어보면 더 잘 찾을 수 있어요.</p>
      )}
      <SourceList
        sources={sources}
        activeRef={activeRef}
        onSelect={toggle}
        onPeek={hoverOpen}
        onPeekEnd={hoverClose}
      />
      {peekSource && (
        <SourcePeek
          source={peekSource}
          answer={answer}
          style={{
            top: peek.top,
            left: peek.left,
            width: peek.width,
            transform: peek.above ? 'translateY(-100%)' : undefined,
          }}
          onEnter={cancel}
          onLeave={hoverClose}
          onClose={() => setPeek(null)}
          onOpenSource={
            onOpenSource &&
            ((source) => {
              setPeek(null)
              onOpenSource(source)
            })
          }
        />
      )}
    </div>
  )
}
