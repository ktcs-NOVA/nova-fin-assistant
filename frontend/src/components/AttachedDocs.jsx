// 관리자 검토 상세의 "첨부 서류" 카드: 직원이 이 정산 건에 붙여 보낸 증빙 서류.
// 정산 유형별로 받아야 하는 서류(지출 결과서·회의록·출장보고서 …) 중 무엇이 왔고 무엇이 안 왔는지 먼저 보여 주고,
// 받은 서류는 눌러서 펼쳐 봅니다 (지출 결과서는 양식 그대로, 나머지는 작성한 본문).

import { useEffect, useState } from 'react'
import { listSubmissionDocuments } from '../api/client.js'
import FormSheet from './FormSheet.jsx'

const LABEL = { 지출결과서: '지출 결과서 · 검수확인서' }
const name = (kind) => LABEL[kind] ?? kind
const when = (iso) => {
  const t = new Date(iso)
  return Number.isNaN(t.getTime()) ? '' : `${t.getMonth() + 1}월 ${t.getDate()}일 ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`
}

export default function AttachedDocs({ code }) {
  const [data, setData] = useState(null)   // null = 불러오는 중
  const [error, setError] = useState('')
  const [openId, setOpenId] = useState(null)

  useEffect(() => {
    let alive = true
    listSubmissionDocuments(code)
      .then((d) => { if (alive) setData(d) })
      .catch((e) => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [code])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="card"><span className="hint">불러오는 중…</span></div>

  const got = new Set(data.documents.map((d) => d.kind))
  return (
    <div className="card attached-docs">
      <ul className="attached-need">
        {data.expected.map((k) => (
          <li key={k}>
            <span className={`badge ${got.has(k) ? 'good' : 'bad'}`}>{got.has(k) ? '받음' : '미제출'}</span>
            {name(k)}
          </li>
        ))}
      </ul>
      {data.missing.length > 0 && (
        <p className="hint">아직 오지 않은 서류가 {data.missing.length}종 있어요. 직원이 확인을 마치고 보내면 여기에 붙습니다.</p>
      )}

      {data.documents.map((d) => (
        <div key={d.id} className="attached-doc">
          <button type="button" className="attached-head" aria-expanded={openId === d.id} onClick={() => setOpenId(openId === d.id ? null : d.id)}>
            <span><b>{name(d.kind)}</b> <span className="hint">{d.writer} · {when(d.sent_at)} 보냄</span></span>
            <span className="link-btn">{openId === d.id ? '접기' : '펼쳐 보기'}</span>
          </button>
          {openId === d.id && (d.form
            ? <FormSheet form={d.form} />
            : <pre className="message-box">{d.draft}</pre>)}
        </div>
      ))}
    </div>
  )
}
