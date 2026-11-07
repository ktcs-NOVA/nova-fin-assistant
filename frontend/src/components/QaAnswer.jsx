// 규정 Q&A 답변 카드 (U-01 · U-03)
// 데이터 모양은 docs/API.md 3-1 의 응답과 같습니다: { answer, grounded, sources[] }
// 본문의 [1] 같은 인용 번호를 버튼으로 바꿔, 누르면 아래 출처 목록의 같은 번호가 강조됩니다.

import { useState } from 'react'
import GroundNotice from './GroundNotice.jsx'
import SourceList from './SourceList.jsx'

// "…지급합니다[1]." → ['…', <묶음: '지급합니다' + 인용 버튼 1>, '.']
// 인용 번호가 앞 단어와 다른 줄로 떨어지지 않도록 마지막 단어와 함께 묶습니다.
function withCitations(text, refs, activeRef, onSelect) {
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
        onClick={() => onSelect(ref)}
        aria-label={`근거 ${ref}번 보기`}
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
          {word[2]}
          {cite}
        </span>,
      )
    } else {
      out.push(cite)
    }
  })
  return out
}

export default function QaAnswer({ result }) {
  const [activeRef, setActiveRef] = useState(null)
  const { answer = '', sources = [] } = result
  const grounded = result.grounded ?? sources.length > 0
  const refs = new Set(sources.map((s, i) => s.ref ?? i + 1))

  return (
    <div className="answer">
      <div className="answer-head">
        <GroundNotice grounded={grounded} count={sources.length} />
      </div>
      <p className="answer-text">{withCitations(answer, refs, activeRef, setActiveRef)}</p>
      <SourceList sources={sources} activeRef={activeRef} onSelect={setActiveRef} />
    </div>
  )
}
