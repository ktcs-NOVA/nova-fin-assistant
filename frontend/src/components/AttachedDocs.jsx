// 관리자 검토 상세의 "첨부 서류": 직원이 이 정산 건에 붙여 보낸 증빙 서류를 승인·반려 판단 바로 위에 펼쳐서 보여 줍니다.
// 위쪽 단추 줄에 받아야 하는 서류가 "받음 / 미제출"로 나오고, 받은 서류는 단추를 눌러 바꿔 봅니다 (처음 것은 열린 채로).
// 지출 결과서·회의록·출장보고서는 직원이 본 양식 그대로(영수증 사진 포함), 그 밖의 서류는 작성한 본문으로 보입니다.

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
  const [data, setData] = useState(null)       // null = 불러오는 중
  const [error, setError] = useState('')
  const [openId, setOpenId] = useState(undefined)   // undefined = 아직 고르지 않음(첫 서류를 엶), null = 접음

  useEffect(() => {
    let alive = true
    listSubmissionDocuments(code)
      .then((d) => { if (alive) setData(d) })
      .catch((e) => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [code])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="card"><span className="hint">불러오는 중…</span></div>

  const docs = data.documents
  const shown = openId === undefined ? docs[0] : docs.find((d) => d.id === openId)
  // 받아야 하는 서류 중 아직 안 온 것 + 받은 서류 전부 (받아야 할 목록에 없는 서류도 왔으면 보여 줌)
  const missing = data.missing

  return (
    <div className="card attached-docs">
      <div className="attached-tabs" role="tablist" aria-label="첨부 서류">
        {docs.map((d) => (
          <button key={d.id} type="button" role="tab" aria-selected={shown?.id === d.id}
            className={`attached-tab${shown?.id === d.id ? ' on' : ''}`} onClick={() => setOpenId(shown?.id === d.id ? null : d.id)}>
            <span className="badge good">받음</span>{name(d.kind)}
          </button>
        ))}
        {missing.map((k) => (
          <span key={k} className="attached-tab off"><span className="badge bad">미제출</span>{name(k)}</span>
        ))}
      </div>

      {docs.length === 0 ? (
        <p className="hint">직원이 아직 서류를 보내지 않았어요. 직원이 서류를 확인하고 “관리자에게 보내기”를 누르면 여기에 바로 보입니다.</p>
      ) : missing.length > 0 ? (
        <p className="hint">아직 오지 않은 서류가 {missing.length}종 있어요. 받은 서류만으로 판단하기 어렵다면 반려 메시지에 적어 요청하세요.</p>
      ) : (
        <p className="hint">받아야 하는 서류가 모두 왔어요. 단추를 눌러 서류를 바꿔 볼 수 있어요.</p>
      )}

      {shown && (
        <div className="attached-doc">
          <div className="attached-head">
            <span><b>{name(shown.kind)}</b> <span className="hint">{shown.writer} · {when(shown.sent_at)} 보냄</span></span>
            <button type="button" className="link-btn" onClick={() => setOpenId(null)}>접기</button>
          </div>
          {shown.form ? <FormSheet form={shown.form} /> : <pre className="message-box">{shown.draft}</pre>}
        </div>
      )}
    </div>
  )
}
