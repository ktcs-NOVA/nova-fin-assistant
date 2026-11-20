// 규정 원문 보기 (U-03): 규정을 골라 조문·별표를 원래 순서대로 읽고, 규정 안에서 검색합니다.
// focus 를 주면 그 조항으로 이동해 잠깐 강조합니다 (답변 근거의 "원문에서 보기").
//   focus = { regulation: '여비규정', article: '제14조', excerpt: '…', nonce: 1 }

import { useEffect, useMemo, useRef, useState } from 'react'
import { getRegulation, listRegulations } from '../api/client.js'
import { parseTable } from '../utils/excerpt.js'
import Marked from './Marked.jsx'
import RegTable from './RegTable.jsx'

const APPROVAL_ARROW = '→ 전결권자'

function sectionLabel(s) {
  if (s.head) return `${s.article} · ${s.head}`
  return s.title ? `${s.article} ${s.title}` : s.article
}

function SectionBody({ section, query }) {
  if (section.kind === 'table') {
    const table = parseTable(section.content)
    if (table) return <RegTable table={table} query={query} />
  }
  if (section.content.includes(APPROVAL_ARROW)) {
    // 전결표: 한 줄이 '업무 > 세부업무 → 전결권자: 부서장'
    const [first, ...rest] = section.content.split('\n')
    return (
      <>
        {first.startsWith('<별표>') ? null : <p className="rule-text"><Marked text={first} query={query} /></p>}
        <ul className="rule-approvals">
          {rest.map((line, i) => (
            <li key={i} className={line.startsWith('※') ? 'note' : undefined}>
              <Marked text={line} query={query} />
            </li>
          ))}
        </ul>
      </>
    )
  }
  return <p className="rule-text"><Marked text={section.content} query={query} /></p>
}

// 답변 근거(규정명·조항·본문)와 맞는 조항 찾기. 같은 '별표'가 여러 구역이면 본문 첫 줄로 고름
function findSection(sections, focus) {
  const same = sections.filter((s) => s.article === focus.article)
  if (same.length <= 1) return same[0]
  const firstLine = focus.excerpt?.split('\n')[0] ?? ''
  return same.find((s) => s.content.startsWith(firstLine)) ?? same[0]
}

export default function RegulationViewer({ focus }) {
  const [list, setList] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [details, setDetails] = useState({})   // id → 원문 (한 번 받은 건 다시 안 받음)
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [flashKey, setFlashKey] = useState(null)
  const [seenFocus, setSeenFocus] = useState(null)   // 마지막으로 처리한 focus
  const [pending, setPending] = useState(null)       // 원문이 오면 이동할 조항
  const refs = useRef({})

  useEffect(() => {
    listRegulations()
      .then((regs) => {
        setList(regs)
        setSelectedId((id) => id ?? regs[0]?.id ?? null)
      })
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (selectedId == null || details[selectedId]) return
    getRegulation(selectedId)
      .then((doc) => setDetails((prev) => ({ ...prev, [selectedId]: doc })))
      .catch((e) => setError(e.message))
  }, [selectedId, details])

  // 답변 근거에서 넘어오면: 그 규정을 고르고 검색을 비운 뒤, 원문이 오면 그 조항으로 이동
  // (props 가 바뀐 걸 그리는 중에 바로 반영 — React 가 권하는 '파생 상태' 방식)
  if (focus && list && focus !== seenFocus) {
    setSeenFocus(focus)
    const reg = list.find((r) => r.title === focus.regulation)
    if (reg) {
      setPending(focus)
      setQuery('')
      setSelectedId(reg.id)
    }
  }

  const doc = selectedId != null ? details[selectedId] : null

  useEffect(() => {
    if (!doc || !pending || doc.title !== pending.regulation) return undefined
    const section = findSection(doc.sections, pending)
    // 화면이 그려진 다음 이동하고 잠깐 강조
    const frame = requestAnimationFrame(() => {
      setPending(null)
      if (!section) return
      refs.current[section.key]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      setFlashKey(section.key)
      setTimeout(() => setFlashKey(null), 2400)
    })
    return () => cancelAnimationFrame(frame)
  }, [doc, pending])

  const visible = useMemo(() => {
    if (!doc) return []
    const q = query.trim().toLowerCase()
    if (!q) return doc.sections
    return doc.sections.filter((s) =>
      [s.article, s.title, s.head, s.content].some((v) => v?.toLowerCase().includes(q)),
    )
  }, [doc, query])

  function jump(key) {
    refs.current[key]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  if (error) return <div className="error">{error}</div>
  if (!list) return <p className="loading">규정 목록을 불러오는 중…</p>
  if (!list.length) return <p className="hint">등록된 규정이 없어요. 관리자에게 규정 적재를 요청해 주세요.</p>

  return (
    <div className="rules">
      <div className="rules-bar">
        <div className="chips rules-docs" role="tablist" aria-label="규정 선택">
          {list.map((r) => (
            <button
              key={r.id}
              type="button"
              role="tab"
              aria-selected={r.id === selectedId}
              className={`chip ${r.id === selectedId ? 'on' : ''}`}
              onClick={() => setSelectedId(r.id)}
            >
              {r.title}
            </button>
          ))}
        </div>
        <input
          type="search"
          className="rules-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="이 규정에서 찾기  예) 숙박비, 자가용"
          aria-label="규정 안에서 찾기"
        />
      </div>

      {!doc ? (
        <p className="loading">원문을 불러오는 중…</p>
      ) : (
        <>
          <p className="hint rules-meta">
            {doc.title}
            {doc.revised_at && ` · 최종 개정 ${doc.revised_at}`}
            {query.trim() && ` · "${query.trim()}" ${visible.length}개 조항`}
          </p>

          {/* 좁은 화면에서는 목차 대신 고르기 상자 */}
          <select className="rules-jump" value="" onChange={(e) => jump(e.target.value)} aria-label="조항으로 이동">
            <option value="">조항으로 이동…</option>
            {visible.map((s) => (
              <option key={s.key} value={s.key}>{sectionLabel(s)}</option>
            ))}
          </select>

          <div className="rules-layout">
            <nav className="rules-toc" aria-label="목차">
              {visible.map((s, i) => (
                <div key={s.key}>
                  {s.chapter && s.chapter !== visible[i - 1]?.chapter && <div className="toc-chapter">{s.chapter}</div>}
                  <button type="button" className={`toc-item ${s.kind}`} onClick={() => jump(s.key)}>
                    {sectionLabel(s)}
                  </button>
                </div>
              ))}
            </nav>

            <div className="rules-body">
              {visible.length === 0 && <p className="hint">찾는 말이 들어간 조항이 없어요.</p>}
              {visible.map((s) => (
                <article
                  key={s.key}
                  ref={(el) => { refs.current[s.key] = el }}
                  className={`rule ${s.kind} ${flashKey === s.key ? 'flash' : ''}`}
                >
                  <header className="rule-head">
                    <strong><Marked text={sectionLabel(s)} query={query} /></strong>
                    {s.revised_at && <span className="source-date">개정 {s.revised_at}</span>}
                  </header>
                  {s.kind === 'form' ? (
                    <details>
                      <summary>서식 내용 보기</summary>
                      <p className="rule-text"><Marked text={s.content} query={query} /></p>
                    </details>
                  ) : (
                    <SectionBody section={s} query={query} />
                  )}
                </article>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
