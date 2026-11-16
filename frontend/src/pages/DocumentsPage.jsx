// 문서 작업 (U-02): 출장보고서·회의록·출장원·지출 결과서를 쓰다 말아도 저장해 두고 이어 쓰는 곳.
// 정산 화면에서 넘어오면(param.newDoc: { kind, fields, origin, submission_code }) 그 값이 채워진 새 서류 작성으로 바로 들어갑니다.
// 지출 결과서(+검수확인서)는 줄글 초안이 아니라 양식이라 전용 편집기(ExpenseReportEditor)로 엽니다.

import { useEffect, useState } from 'react'
import { DOC_KINDS, deleteDocument, listDocuments } from '../api/client.js'
import DocumentEditor, { DOC_SCHEMA } from '../components/DocumentEditor.jsx'
import ExpenseReportEditor from '../components/ExpenseReportEditor.jsx'
import { REPORT } from '../utils/claimToDocs.js'
import Icon from '../components/Icons.jsx'

const KIND_ICON = { 출장보고서: 'trip', 회의록: 'meeting', 출장원: 'card', [REPORT]: 'card' }
const KIND_CLASS = { 출장보고서: '', 회의록: 'ico-meeting', 출장원: 'ico-card', [REPORT]: 'ico-card' }
const KIND_NAME = { [REPORT]: '지출 결과서 · 검수확인서' }

const when = (iso) => {
  const t = new Date(iso)
  return Number.isNaN(t.getTime()) ? '' : `${t.getMonth() + 1}월 ${t.getDate()}일 ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`
}

export default function DocumentsPage(props) {
  const [rows, setRows] = useState(null)       // null = 불러오는 중
  const [editing, setEditing] = useState(() => (props.param?.newDoc ? { draft: '', ...props.param.newDoc } : null)) // null | 서류 객체(id 없으면 새 서류)
  const [picking, setPicking] = useState(false)
  const [confirmId, setConfirmId] = useState(null)
  const [error, setError] = useState('')

  function reload() {
    return listDocuments().then(setRows).catch((e) => { setError(e.message); setRows([]) })
  }
  useEffect(() => { reload() }, [])

  async function remove(id) {
    setError('')
    try {
      await deleteDocument(id)
      setConfirmId(null)
      await reload()
    } catch (e) {
      setError(e.message)
    }
  }

  if (editing) {
    const Editor = editing.kind === REPORT ? ExpenseReportEditor : DocumentEditor
    return <Editor key={editing.id ?? 'new'} doc={editing} onChanged={reload} onBack={() => { setEditing(null); reload() }} />
  }

  const working = (rows ?? []).filter((d) => d.status !== '작성 완료')
  const done = (rows ?? []).filter((d) => d.status === '작성 완료')

  return (
    <div className="documents">
      <h1>문서 작업</h1>
      <p className="hint">쓰던 서류를 저장해 두고, 나중에 이어서 쓸 수 있어요. 정산 건에서 만든 서류는 확인을 마치면 관리자에게 보낼 수 있어요.</p>

      {error && <div className="error">{error}</div>}

      {picking ? (
        <div className="card">
          <div className="card-head">
            <h2>어떤 서류를 쓸까요?</h2>
            <button type="button" className="btn small" onClick={() => setPicking(false)}>닫기</button>
          </div>
          <div className="doc-kinds">
            {DOC_KINDS.map((k) => (
              <button key={k} type="button" className="tile doc-kind" onClick={() => { setPicking(false); setEditing({ kind: k, fields: {}, draft: '' }) }}>
                <span className={`tile-icon ${KIND_CLASS[k]}`}><Icon name={KIND_ICON[k]} size={28} /></span>
                <span className="tile-title">{k}</span>
                <span className="tile-desc">{DOC_SCHEMA[k].desc}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="btn-row between doc-top">
          <span className="hint">{rows === null ? '불러오는 중…' : `작성 중 ${working.length}건 · 작성 완료 ${done.length}건`}</span>
          <button type="button" className="btn primary" onClick={() => setPicking(true)}>＋ 새 서류 쓰기</button>
        </div>
      )}

      {rows !== null && rows.length === 0 && !picking && (
        <div className="empty">
          <p>아직 저장한 서류가 없어요.</p>
          <p className="hint">“새 서류 쓰기”로 출장보고서·회의록·출장원을 시작해 보세요.</p>
        </div>
      )}

      {[['작성 중인 문서', working], ['작성 완료', done]].map(([label, list]) =>
        list.length === 0 ? null : (
          <section key={label}>
            <h2 className="home-sub">{label}</h2>
            <ul className="doc-list">
              {list.map((d) => (
                <li key={d.id} className="card doc-item">
                  <span className={`tile-icon ${KIND_CLASS[d.kind]}`}><Icon name={KIND_ICON[d.kind]} size={24} /></span>
                  <div className="doc-item-main">
                    <div className="recent-name">{d.title}</div>
                    <div className="hint">{KIND_NAME[d.kind] ?? d.kind}{d.submission_code ? ` · 정산 ${d.submission_code}` : ''} · {when(d.updated_at)} 수정{d.draft ? ' · 초안 있음' : ''}</div>
                  </div>
                  <span className={`badge ${d.status === '작성 완료' ? 'good' : 'muted'}`}>{d.sent_at ? '관리자에게 보냄' : d.status}</span>
                  {confirmId === d.id ? (
                    <span className="doc-actions">
                      <button type="button" className="btn small danger" onClick={() => remove(d.id)}>삭제 확인</button>
                      <button type="button" className="btn small" onClick={() => setConfirmId(null)}>취소</button>
                    </span>
                  ) : (
                    <span className="doc-actions">
                      <button type="button" className="btn small primary" onClick={() => setEditing(d)}>{d.status === '작성 완료' ? '열기' : '이어서 쓰기'}</button>
                      <button type="button" className="btn small" onClick={() => setConfirmId(d.id)}>삭제</button>
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ),
      )}
    </div>
  )
}
