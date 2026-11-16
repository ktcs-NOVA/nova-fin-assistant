// 문서 작업 (U-02): 출장보고서·회의록·출장원·지출 결과서를 쓰다 말아도 저장해 두고 이어 쓰는 곳.
// 정산 화면에서 넘어오면(param.newDoc: { kind, fields, origin, submission_code }) 그 값이 채워진 새 서류 작성으로 바로 들어갑니다.
// 지출 결과서(+검수확인서)와, 정산 건에서 만든 회의록·출장보고서는 줄글 초안이 아니라 양식이라 양식 편집기(ExpenseReportEditor)로 엽니다.
// "새 서류 쓰기"는 ① 서류 종류 ② 어느 정산 건의 서류인지 를 차례로 고르고 양식으로 들어갑니다 (양식이 금액·날짜를 정산 건에서 읽기 때문).
// 예전에 정산 건 없이 써 둔 회의록·출장보고서·출장원은 목록에서 그대로 열리고, 줄글 초안 편집기(DocumentEditor)를 씁니다.

import { useEffect, useState } from 'react'
import { deleteDocument, listDocuments, listMySubmissions } from '../api/client.js'
import DocumentEditor from '../components/DocumentEditor.jsx'
import ExpenseReportEditor from '../components/ExpenseReportEditor.jsx'
import { REPORT } from '../utils/claimToDocs.js'
import { CLAIM } from '../utils/claimTypes.js'
import Icon from '../components/Icons.jsx'

const KIND_ICON = { 출장보고서: 'trip', 회의록: 'meeting', 출장원: 'card', [REPORT]: 'card' }
const KIND_CLASS = { 출장보고서: '', 회의록: 'ico-meeting', 출장원: 'ico-card', [REPORT]: 'ico-card' }
const KIND_NAME = { [REPORT]: '지출 결과서 · 검수확인서' }
const FORM_KINDS = [REPORT, '회의록', '출장보고서']
// 새로 쓸 수 있는 서류 (기본 양식 3종). fits: 이 서류를 붙일 수 있는 정산 유형
const NEW_KINDS = [
  { kind: REPORT, desc: '정산한 금액·날짜·영수증을 양식에 채워 드려요. 검수자만 적으면 돼요.', need: '정산', fits: () => true },
  { kind: '회의록', desc: '회의주제·일시·참여자·집행금액을 채워 드려요. 회의 내용만 적으면 돼요.', need: '회의비 정산', fits: (s) => s.type === CLAIM.MEETING },
  { kind: '출장보고서', desc: '출장일자·명단·집행금액을 채워 드려요. 출장지와 출장 내용만 적으면 돼요.', need: '출장 정산', fits: (s) => String(s.type).includes('출장') },
]
const won = (n) => Number(n ?? 0).toLocaleString('ko-KR') + '원'
const isForm = (d) => d.kind === REPORT || (FORM_KINDS.includes(d.kind) && Boolean(d.submission_code))

const when = (iso) => {
  const t = new Date(iso)
  return Number.isNaN(t.getTime()) ? '' : `${t.getMonth() + 1}월 ${t.getDate()}일 ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`
}

export default function DocumentsPage(props) {
  const [rows, setRows] = useState(null)       // null = 불러오는 중
  const [editing, setEditing] = useState(() => (props.param?.newDoc ? { draft: '', ...props.param.newDoc } : null)) // null | 서류 객체(id 없으면 새 서류)
  const [picking, setPicking] = useState(false)     // 새 서류 고르는 중
  const [pickKind, setPickKind] = useState(null)   // 고른 서류 종류 (다음은 정산 건 고르기)
  const [subs, setSubs] = useState(null)           // 내 정산 건 (null = 아직 안 불러옴)
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

  function closePicker() {
    setPicking(false)
    setPickKind(null)
  }

  // 서류 종류를 고르면 내 정산 건을 불러와 어느 건의 서류인지 고르게 함
  function chooseKind(k) {
    setPickKind(k)
    setError('')
    if (subs === null) listMySubmissions().then((d) => setSubs(d.items ?? [])).catch((e) => { setError(e.message); setSubs([]) })
  }

  // 정산 건을 고르면: 이미 그 건의 같은 서류가 있으면 이어 쓰고, 없으면 새 양식
  function chooseSubmission(s) {
    const existing = (rows ?? []).find((d) => d.kind === pickKind.kind && d.submission_code === s.id)
    closePicker()
    setEditing(existing ?? { kind: pickKind.kind, fields: {}, draft: '', submission_code: s.id })
  }

  if (editing) {
    const Editor = isForm(editing) ? ExpenseReportEditor : DocumentEditor
    return <Editor key={editing.id ?? 'new'} doc={editing} onChanged={reload} onBack={() => { setEditing(null); reload() }} />
  }

  const working = (rows ?? []).filter((d) => d.status !== '작성 완료')
  const done = (rows ?? []).filter((d) => d.status === '작성 완료')

  return (
    <div className="documents">
      <h1>문서 작업</h1>
      <p className="hint">쓰던 서류를 저장해 두고, 나중에 이어서 쓸 수 있어요. 정산 건에서 만든 서류는 확인을 마치면 관리자에게 보낼 수 있어요.</p>

      {error && <div className="error">{error}</div>}

      {picking && !pickKind && (
        <div className="card">
          <div className="card-head">
            <h2>어떤 서류를 쓸까요?</h2>
            <button type="button" className="btn small" onClick={closePicker}>닫기</button>
          </div>
          <p className="hint">서류는 제출한 정산 건에 붙여서 써요. 금액·날짜·참석자를 정산 건에서 그대로 가져옵니다.</p>
          <div className="doc-kinds">
            {NEW_KINDS.map((k) => (
              <button key={k.kind} type="button" className="tile doc-kind" onClick={() => chooseKind(k)}>
                <span className={`tile-icon ${KIND_CLASS[k.kind]}`}><Icon name={KIND_ICON[k.kind]} size={28} /></span>
                <span className="tile-title">{KIND_NAME[k.kind] ?? k.kind}</span>
                <span className="tile-desc">{k.desc}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {picking && pickKind && (() => {
        const fit = (subs ?? []).filter(pickKind.fits)
        return (
          <div className="card">
            <div className="card-head">
              <h2>어느 정산의 {KIND_NAME[pickKind.kind] ?? pickKind.kind}인가요?</h2>
              <span className="btn-row">
                <button type="button" className="btn small" onClick={() => setPickKind(null)}>← 서류 다시 고르기</button>
                <button type="button" className="btn small" onClick={closePicker}>닫기</button>
              </span>
            </div>
            {subs === null ? (
              <div className="empty">불러오는 중…</div>
            ) : fit.length === 0 ? (
              <div className="empty">
                <p>이 서류를 붙일 {pickKind.need} 건이 아직 없어요.</p>
                <p className="hint">먼저 정산을 제출하면 그 건의 금액·날짜로 서류를 만들 수 있어요.</p>
                <button type="button" className="btn primary" onClick={() => props.onNavigate?.('type')}>정산하러 가기 →</button>
              </div>
            ) : (
              <ul className="alert-list">
                {fit.map((sub) => {
                  const has = (rows ?? []).some((d) => d.kind === pickKind.kind && d.submission_code === sub.id)
                  return (
                    <li key={sub.id}>
                      <button type="button" className="alert-row plain" onClick={() => chooseSubmission(sub)}>
                        <span className="alert-main">
                          <span className="recent-name">{sub.type} · {sub.purpose}</span>
                          <span className="hint">{sub.date} · {sub.id}{has ? ' · 쓰던 서류가 있어요' : ''}</span>
                        </span>
                        <span className="alert-side">
                          <span className="alert-amount">{won(sub.amount)}</span>
                          <span className="link-btn">{has ? '이어서 쓰기 →' : '이 건으로 쓰기 →'}</span>
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        )
      })()}

      {!picking && (
        <div className="btn-row between doc-top">
          <span className="hint">{rows === null ? '불러오는 중…' : `작성 중 ${working.length}건 · 작성 완료 ${done.length}건`}</span>
          <button type="button" className="btn primary" onClick={() => setPicking(true)}>＋ 새 서류 쓰기</button>
        </div>
      )}

      {rows !== null && rows.length === 0 && !picking && (
        <div className="empty">
          <p>아직 저장한 서류가 없어요.</p>
          <p className="hint">“새 서류 쓰기”에서 서류와 정산 건을 고르면 지출 결과서·회의록·출장보고서를 양식으로 쓸 수 있어요.</p>
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
