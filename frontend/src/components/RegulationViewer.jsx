// 규정 원문 보기 (U-03): 적재해 둔 규정을 조항 순서 그대로 읽습니다. 챗봇 답변의 근거와 같은 자료입니다.
// 왼쪽에서 규정을 고르고, 오른쪽에서 조항을 펼쳐 읽거나 낱말로 찾습니다.
//   focus = { regulation: '여비규정', article: '제13조 제5항' } 를 주면 그 규정을 열고 그 조항을 펼쳐 보여 줍니다
//   (답변의 근거 조항에서 "원문에서 보기"로 넘어올 때).

import { useEffect, useMemo, useRef, useState } from 'react'
import { getRegulation, listRegulations } from '../api/client.js'
import { parseTable } from '../utils/excerpt.js'
import { TableView } from './SourcePeek.jsx'

const PAGE = 120   // 한 번에 그리는 조항 수 (별표가 수백 줄인 규정이 있어서)
const KIND = { table: '별표', form: '서식' }
const NONE = new Set()

// '제13조 제5항' 은 '제13조' 조항에 있음. 가장 길게 맞는 조항을 고릅니다 ('제3조' 보다 '제3조의2').
function findSection(sections, article) {
  if (!article) return null
  let best = null
  for (const s of sections) {
    if (!s.article) continue
    const hit = article === s.article || article.startsWith(`${s.article} `)
    if (hit && (!best || s.article.length > best.article.length)) best = s
  }
  return best
}

// 조항 제목 줄: '제13조 (교통비)'. 제목이 없는 별표는 본문 첫 줄을 씁니다.
function heading(s) {
  if (s.title) return `${s.article ?? ''} ${s.type === 'article' ? `(${s.title})` : s.title}`.trim()
  const first = s.content.split('\n').find((l) => l.trim())?.replace(/\s*<개정[^>]*>\s*/g, ' ').trim() ?? ''
  return first.length > 70 ? `${first.slice(0, 70)}…` : first || s.article || ''
}

function Body({ section }) {
  const table = section.type === 'table' ? parseTable(section.content) : null
  if (table) return <TableView table={table} highlight={NONE} />
  return <p className="reg-text">{section.content}</p>
}

export default function RegulationViewer({ focus }) {
  const [list, setList] = useState(null)
  const [id, setId] = useState(null)
  const [reg, setReg] = useState(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(PAGE)
  const [openSeq, setOpenSeq] = useState(null)   // 근거 조항에서 넘어와 펼쳐 둘 조항
  const focusRef = useRef(null)

  // 규정 목록: 넘어온 규정이 있으면 그것, 없으면 첫 번째 규정을 엽니다
  useEffect(() => {
    let alive = true
    listRegulations()
      .then((rows) => {
        if (!alive) return
        setList(rows)
        const wanted = focus?.regulation && rows.find((r) => r.title === focus.regulation)
        setId((wanted || rows[0])?.id ?? null)
      })
      .catch((e) => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [focus?.regulation])

  // 고른 규정의 원문
  useEffect(() => {
    if (id == null) return undefined
    let alive = true
    getRegulation(id)
      .then((data) => {
        if (!alive) return
        const target = data.title === focus?.regulation ? findSection(data.sections, focus.article) : null
        setOpenSeq(target?.seq ?? null)
        // 넘어온 조항이 뒤쪽에 있어도 보이도록 그 조항까지는 그립니다
        setLimit(target ? Math.max(PAGE, data.sections.indexOf(target) + 20) : PAGE)
        setReg(data)
        setError('')
      })
      .catch((e) => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [id, focus?.regulation, focus?.article])

  // 넘어온 조항으로 화면을 옮김
  useEffect(() => {
    if (reg && reg.id === id && openSeq != null) focusRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  }, [reg, id, openSeq])

  function pick(next) {
    if (next === id) return
    setId(next)
    setQuery('')
  }

  const loading = reg?.id !== id
  const word = query.trim()
  const matches = useMemo(() => {
    if (!reg) return []
    if (!word) return reg.sections
    return reg.sections.filter((s) => `${s.article ?? ''} ${s.title ?? ''} ${s.content}`.includes(word))
  }, [reg, word])
  const shown = matches.slice(0, limit)

  if (error && !list) return <div className="error">{error}</div>
  if (!list) return <div className="empty">규정 목록을 불러오는 중…</div>
  if (!list.length) return <div className="empty">아직 등록된 규정이 없어요.</div>

  return (
    <div className="reg">
      <nav className="reg-list" aria-label="규정 목록">
        {list.map((r) => (
          <button key={r.id} type="button" className={`reg-item${r.id === id ? ' on' : ''}`} aria-current={r.id === id ? 'true' : undefined} onClick={() => pick(r.id)}>
            <span className="reg-item-title">{r.title}</span>
            <span className="reg-item-meta">
              {r.revised_at ? `개정 ${r.revised_at}` : '개정일 미상'}
              {r.admin_only && <span className="badge muted">관리자용</span>}
            </span>
          </button>
        ))}
      </nav>

      <div className="reg-doc">
        {error && <div className="error">{error}</div>}
        {loading && !error && <div className="empty">원문을 불러오는 중…</div>}
        {!loading && reg && (
          <>
            <div className="reg-head">
              <h2>{reg.title}</h2>
              <span className="hint">
                {reg.revised_at ? `최종 개정 ${reg.revised_at} · ` : ''}조항·별표·서식 {reg.sections.length}개
                {reg.source_url && <> · <a className="source-link" href={reg.source_url} target="_blank" rel="noreferrer">공시 원문</a></>}
              </span>
            </div>
            <label className="reg-search">
              <input type="search" aria-label="이 규정 안에서 찾기" value={query} placeholder="이 규정 안에서 찾기  예) 숙박비" onChange={(e) => { setQuery(e.target.value); setLimit(PAGE) }} />
              {word && <span className="hint">{matches.length}개 찾음</span>}
            </label>

            {word && matches.length === 0 && <div className="empty">‘{word}’가 들어간 조항이 없어요. 다른 낱말로 찾아보거나, ‘NOVA에게 물어보기’에서 물어보세요.</div>}

            <div className="reg-sections">
              {shown.map((s, i) => {
                const chapter = s.chapter && s.chapter !== shown[i - 1]?.chapter ? s.chapter : null
                const focused = s.seq === openSeq
                return (
                  <div key={s.seq} ref={focused ? focusRef : undefined}>
                    {chapter && <div className="reg-chapter">{chapter}</div>}
                    {/* 찾기 결과와 넘어온 조항은 펼쳐서, 나머지는 접어서 */}
                    <details className={`reg-section${focused ? ' focus' : ''}`} open={Boolean(word) || focused}>
                      <summary>
                        {KIND[s.type] && <span className="badge muted">{KIND[s.type]}</span>}
                        <span className="reg-section-title">{heading(s)}</span>
                        {s.revised_at && <span className="source-date">개정 {s.revised_at}</span>}
                      </summary>
                      <div className="reg-body"><Body section={s} /></div>
                    </details>
                  </div>
                )
              })}
            </div>
            {matches.length > shown.length && (
              <button type="button" className="btn reg-more" onClick={() => setLimit((n) => n + PAGE)}>
                더 보기 ({shown.length} / {matches.length})
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}
