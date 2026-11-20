// 기본 양식 작성 화면: 지출 결과서 + 검수확인서 · 회의록 · 출장보고서 (정산 건에서 만든 서류).
// 정산 건의 금액·날짜·건명·참석자는 자동으로 들어가고, AI 는 문구를 제안하거나(지출 결과서) 적어 둔 메모를 다듬습니다(회의록·출장보고서).
// 직원은 ① 직접 적어야 하는 칸만 채우고 ② 내용을 읽어 확인한 뒤 ③ 관리자에게 보냅니다.
// 숫자는 항상 정산 건에서 읽으므로 이 화면에서 고칠 수 없습니다 (양식과 정산 금액이 어긋나지 않게).

import { useEffect, useRef, useState } from 'react'
import { createDocument, fillDocumentForm, getDocumentForm, sendDocument, updateDocument } from '../api/client.js'
import FormSheet, { FormLegend } from './FormSheet.jsx'
import { editableCells, editableWithContext, formSummary, sourceOf } from '../utils/formCells.js'

const when = (iso) => {
  const t = new Date(iso)
  return Number.isNaN(t.getTime()) ? '' : `${t.getMonth() + 1}월 ${t.getDate()}일 ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`
}
// 양식별 화면 문구
const KINDS = {
  지출결과서: { title: '지출 결과서 · 검수확인서', fill: 'AI 제안 다시 받기', filled: 'AI 제안으로 다시 채웠어요. 직접 고친 칸은 그대로 두었어요.' },
  회의록: { title: '회의록', fill: 'AI로 문장 다듬기', filled: '적어 둔 내용을 회의록 문체로 다듬었어요. 읽어 보고 고칠 곳은 직접 고쳐 주세요.' },
  출장보고서: { title: '출장보고서', fill: 'AI로 문장 다듬기', filled: '적어 둔 내용을 보고서 문체로 다듬었어요. 읽어 보고 고칠 곳은 직접 고쳐 주세요.' },
}
const same = (a, b) => JSON.stringify(a ?? {}) === JSON.stringify(b ?? {})

export default function ExpenseReportEditor({ doc, onBack, onChanged }) {
  const [saved, setSaved] = useState(doc.id ? doc : null)   // 서버에 저장된 서류 (아직 만드는 중이면 null)
  const [form, setForm] = useState(null)                    // 양식 (칸 구성 + 자동 값)
  const [fields, setFields] = useState(doc.id ? (doc.fields ?? {}) : {})   // 고칠 수 있는 칸의 지금 값
  const text = KINDS[doc.kind] ?? KINDS.지출결과서
  const [busy, setBusy] = useState('load')                  // '' | load | save | fill | confirm | send
  const [error, setError] = useState('')
  const [note, setNote] = useState('')
  const [tab, setTab] = useState('write')                   // write = 적을 칸만 모아 보기 | form = 양식 그대로 보기
  const opening = useRef(null)   // 개발 모드에서 effect 가 두 번 돌아도 서류를 한 번만 만들게

  // 처음 들어오면: (없으면 정산 건에서 새로 만들고) 양식을 불러옵니다.
  useEffect(() => {
    let alive = true
    opening.current ??= (async () => {
      const cur = doc.id ? doc : await createDocument({ kind: doc.kind, fields: doc.fields, submission_code: doc.submission_code })
      return { cur, form: await getDocumentForm(cur.id) }
    })()
    opening.current
      .then((r) => { if (alive) { setSaved(r.cur); setFields(r.cur.fields ?? {}); setForm(r.form); onChanged?.() } })
      .catch((e) => { if (alive) setError(e.message) })
      .finally(() => { if (alive) setBusy('') })
    return () => { alive = false }
  }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  const dirty = saved ? !same(fields, saved.fields) : false
  const cells = editableCells(form)
  const todo = cells.filter((c) => c.required && !String(fields[c.key] ?? '').trim())
  const confirmed = Boolean(saved?.confirmed) && !dirty
  const sent = confirmed && saved?.sent_at

  function edit(key, value) {
    setNote('')
    // 직접 고친 칸은 AI 제안 목록에서 빼서 "직접 입력"으로 표시
    setFields((f) => ({ ...f, [key]: value, ai_keys: (f.ai_keys ?? []).filter((k) => k !== key) }))
  }

  function apply(next) {
    setSaved(next)
    setFields(next.fields ?? {})
    onChanged?.()
    return next
  }

  async function run(name, job, doneNote) {
    setBusy(name)
    setError('')
    setNote('')
    try {
      const own = await job()   // job 이 문구를 돌려주면 그 문구를, 아니면 기본 완료 문구를 보여 줌
      setNote(typeof own === 'string' ? own : doneNote ?? '')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy('')
    }
  }

  const persist = async (extra = {}) => apply(await updateDocument(saved.id, { fields, ...extra }))
  const save = () => run('save', () => persist(), '저장했어요. 나중에 문서 작업에서 이어 쓸 수 있어요.')
  const fill = () => run('fill', async () => {
    const before = (dirty ? await persist() : saved).fields
    const next = apply(await fillDocumentForm(saved.id))
    // 다듬은 결과가 원래 글과 같으면(AI 가 꺼져 있거나 숫자가 달라져 쓰지 않은 경우) 그대로라고 알려 줌
    if (same(next.fields, before)) return '고칠 곳을 찾지 못해 그대로 두었어요.'
  }, text.filled)
  const toggleConfirm = (checked) => run('confirm', () => persist({ confirmed: checked }))
  const send = () => run('send', async () => apply(await sendDocument(saved.id)), '관리자에게 보냈어요. 관리자 화면의 이 정산 건에 붙어서 보여요.')

  // 칸으로 이동: 지금 보고 있는 탭에서 그 칸을 찾아 가운데로
  function focusCell(key) {
    requestAnimationFrame(() => {
      const el = document.getElementById(`cell-${key}`)
      el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
      el?.focus({ preventScroll: true })
    })
  }

  // 인쇄는 양식 모양으로: 작성하기 탭이면 양식 탭으로 바꾼 뒤 인쇄
  function print() {
    if (tab === 'form') return window.print()
    setTab('form')
    setTimeout(() => window.print(), 300)
  }

  const code = saved?.submission_code ?? doc.submission_code
  // 회의록·출장보고서의 "AI로 문장 다듬기"는 적어 둔 메모가 있어야 쓸 수 있음 (빈 채로 누르면 빨간 오류 대신 단추를 잠가 둠)
  const memoCell = cells.find((c) => c.multiline)
  const needMemo = Boolean(memoCell) && !String(fields[memoCell.key] ?? '').trim()

  return (
    <div className="doc-editor report-editor">
      <button type="button" className="btn small no-print" onClick={onBack}>← 문서 목록</button>
      <div className="card-head doc-editor-head no-print">
        <h2>{text.title}</h2>
        {saved && <span className={`badge ${sent ? 'good' : confirmed ? 'good' : 'muted'}`}>{sent ? '관리자에게 보냄' : confirmed ? '작성 완료' : '작성 중'}</span>}
      </div>
      {code && <p className="hint doc-source no-print">정산 {code}에서 가져온 건명·금액·날짜·참석자는 여기서 고칠 수 없어요.</p>}

      {error && <div className="error no-print">{error}</div>}
      {busy === 'load' && <div className="empty">양식을 만드는 중…</div>}

      {form && saved && (
        <>
          <div className="doc-toolbar no-print">
            <div className="seg doc-tabs" role="tablist">
              <button type="button" role="tab" aria-selected={tab === 'write'} className={tab === 'write' ? 'on' : ''} onClick={() => setTab('write')}>① 작성하기</button>
              <button type="button" role="tab" aria-selected={tab === 'form'} className={tab === 'form' ? 'on' : ''} onClick={() => setTab('form')}>② 양식으로 보기</button>
            </div>
            {todo.length > 0 ? (
              <div className="doc-todo">
                <span>적을 칸 <b>{todo.length}</b>개</span>
                {todo.map((c) => <button key={c.key} type="button" className="doc-todo-chip" onClick={() => focusCell(c.key)}>{c.label} →</button>)}
              </div>
            ) : (
              <div className="doc-todo done">✓ 적을 칸을 다 채웠어요</div>
            )}
          </div>

          {tab === 'form' && <div className="no-print doc-legend"><FormLegend /></div>}

          {tab === 'write'
            ? <WriteView form={form} fields={fields} onEdit={edit} onShowForm={() => setTab('form')} />
            : <FormSheet form={form} fields={fields} onEdit={edit} />}

          {note && <div className="doc-note no-print">{note}</div>}

          <div className="form-actions-bar no-print">
            <div className="btn-row start">
              <button type="button" className="btn small" disabled={Boolean(busy) || needMemo} title={needMemo ? `${memoCell.label}을 먼저 메모로 적으면 다듬어 드려요` : undefined} onClick={fill}>{busy === 'fill' ? 'AI가 쓰는 중…' : text.fill}</button>
              <button type="button" className="btn small" disabled={Boolean(busy) || !dirty} onClick={save}>{busy === 'save' ? '저장 중…' : dirty ? '저장' : '저장됨'}</button>
              <button type="button" className="btn small" onClick={print}>인쇄 · PDF</button>
            </div>
            <div className="form-actions-send">
              <label className="check-inline doc-confirm">
                <input type="checkbox" checked={confirmed} disabled={Boolean(busy) || todo.length > 0} onChange={(e) => toggleConfirm(e.target.checked)} />
                <span>{todo.length > 0 ? `빈 칸 ${todo.length}개를 먼저 채워 주세요` : '내용을 읽고 확인했어요'}</span>
              </label>
              <button type="button" className="btn primary" disabled={Boolean(busy) || !confirmed || Boolean(sent)} onClick={send}
                title={sent ? `${when(saved.sent_at)}에 보냈어요. 내용을 고치면 다시 보내야 해요.` : '보내면 관리자 화면의 이 정산 건에 증빙 서류로 붙어요.'}>
                {busy === 'send' ? '보내는 중…' : sent ? `보냄 · ${when(saved.sent_at)}` : '관리자에게 보내기'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ① 작성하기: 양식 전체 대신, 직원이 적거나 확인할 칸만 모아서 보여 줍니다.
//   직접 적는 칸(검수자·특이 사항·회의 내용 …)이 위, AI 가 쓴 짧은 문구(상세내역·용도)는 아래에 품명·금액과 함께.
function WriteView({ form, fields, onEdit, onShowForm }) {
  const cells = editableWithContext(form)
  const mine = cells.filter((c) => !c.ai || c.multiline).sort((a, b) => Number(b.required) - Number(a.required))
  const ai = cells.filter((c) => c.ai && !c.multiline)
  const summary = formSummary(form)
  const sheets = [...new Set(ai.map((c) => c.sheet))]

  return (
    <div className="write-view">
      {summary.length > 0 && (
        <div className="card write-summary">
          <div className="write-summary-head">
            <b>정산 건에서 가져온 내용</b>
            <button type="button" className="link-btn" onClick={onShowForm}>양식 전체 보기 →</button>
          </div>
          <dl>{summary.map((r) => <div key={r.label}><dt>{r.label}</dt><dd>{r.value}</dd></div>)}</dl>
        </div>
      )}

      {mine.length > 0 && (
        <div className="card write-group">
          <h3>직접 적어 주세요</h3>
          {mine.map((c) => <WriteField key={c.key} cell={c} fields={fields} onEdit={onEdit} where />)}
        </div>
      )}

      {ai.length > 0 && (
        <div className="card write-group">
          <h3>AI가 쓴 문구 <span className="hint">읽어 보고 고칠 곳만 고쳐요</span></h3>
          {sheets.map((sh) => (
            <div key={sh} className="write-sheet">
              {sheets.length > 1 && <div className="write-sheet-title">{sh}</div>}
              {ai.filter((c) => c.sheet === sh).map((c) => <WriteField key={c.key} cell={c} fields={fields} onEdit={onEdit} />)}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function WriteField({ cell, fields, onEdit, where = false }) {
  const value = String(fields[cell.key] ?? '')
  const src = sourceOf(cell, fields)
  const need = cell.required && !value.trim()
  return (
    <label className={`write-field src-${src}${need ? ' need' : ''}`}>
      <span className="write-label">
        <b>{cell.name}</b>
        {cell.ctx && <span className="hint">{cell.ctx}</span>}
        <span className="write-tags">
          {cell.required && <span className={`write-req${need ? ' on' : ''}`}>{need ? '필수 · 비어 있음' : '필수'}</span>}
          <span className={`form-chip src-${src}`}>{src === 'ai' ? 'AI 작성' : '직접 입력'}</span>
        </span>
      </span>
      <textarea
        id={`cell-${cell.key}`}
        className="write-input"
        rows={cell.multiline ? 7 : 1}
        value={value}
        placeholder={cell.placeholder ?? ''}
        maxLength={cell.limit ?? 60}
        onChange={(e) => onEdit(cell.key, cell.multiline ? e.target.value : e.target.value.replace(/\n/g, ' '))}
      />
      {where && cell.sheet && <span className="write-where hint">{cell.sheet.replace(/\s/g, "")}에 들어가요</span>}
    </label>
  )
}
