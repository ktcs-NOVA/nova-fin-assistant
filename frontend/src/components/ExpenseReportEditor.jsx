// 지출 결과서 + 검수확인서 작성 화면 (기본 양식).
// 정산 건의 금액·날짜·건명은 자동으로 들어가고, AI 가 상세내역·용도 문구를 제안합니다.
// 직원은 ① 직접 적어야 하는 칸(검수자)만 채우고 ② 내용을 읽어 확인한 뒤 ③ 관리자에게 보냅니다.
// 숫자는 항상 정산 건에서 읽으므로 이 화면에서 고칠 수 없습니다 (양식과 정산 금액이 어긋나지 않게).

import { useEffect, useRef, useState } from 'react'
import { createDocument, fillDocumentForm, getDocumentForm, sendDocument, updateDocument } from '../api/client.js'
import FormSheet, { FormLegend } from './FormSheet.jsx'
import { editableCells } from '../utils/formCells.js'

const when = (iso) => {
  const t = new Date(iso)
  return Number.isNaN(t.getTime()) ? '' : `${t.getMonth() + 1}월 ${t.getDate()}일 ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`
}
const same = (a, b) => JSON.stringify(a ?? {}) === JSON.stringify(b ?? {})

export default function ExpenseReportEditor({ doc, onBack, onChanged }) {
  const [saved, setSaved] = useState(doc.id ? doc : null)   // 서버에 저장된 서류 (아직 만드는 중이면 null)
  const [form, setForm] = useState(null)                    // 양식 (칸 구성 + 자동 값)
  const [fields, setFields] = useState(doc.fields ?? {})    // 고칠 수 있는 칸의 지금 값
  const [busy, setBusy] = useState('load')                  // '' | load | save | fill | confirm | send
  const [error, setError] = useState('')
  const [note, setNote] = useState('')
  const opening = useRef(null)   // 개발 모드에서 effect 가 두 번 돌아도 서류를 한 번만 만들게

  // 처음 들어오면: (없으면 정산 건에서 새로 만들고) 양식을 불러옵니다.
  useEffect(() => {
    let alive = true
    opening.current ??= (async () => {
      const cur = doc.id ? doc : await createDocument({ kind: doc.kind, submission_code: doc.submission_code })
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
      await job()
      if (doneNote) setNote(doneNote)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy('')
    }
  }

  const persist = async (extra = {}) => apply(await updateDocument(saved.id, { fields, ...extra }))
  const save = () => run('save', () => persist(), '저장했어요. 나중에 문서 작업에서 이어 쓸 수 있어요.')
  const fill = () => run('fill', async () => {
    if (dirty) await persist()
    apply(await fillDocumentForm(saved.id))
  }, 'AI 제안으로 다시 채웠어요. 직접 고친 칸은 그대로 두었어요.')
  const toggleConfirm = (checked) => run('confirm', () => persist({ confirmed: checked }))
  const send = () => run('send', async () => apply(await sendDocument(saved.id)), '관리자에게 보냈어요. 관리자 화면의 이 정산 건에 붙어서 보여요.')

  function focusCell(key) {
    const el = document.getElementById(`cell-${key}`)
    el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    el?.focus({ preventScroll: true })
  }

  const code = saved?.submission_code ?? doc.submission_code

  return (
    <div className="doc-editor report-editor">
      <button type="button" className="btn small no-print" onClick={onBack}>← 문서 목록</button>
      <div className="card-head doc-editor-head no-print">
        <h2>지출 결과서 · 검수확인서</h2>
        {saved && <span className={`badge ${sent ? 'good' : confirmed ? 'good' : 'muted'}`}>{sent ? '관리자에게 보냄' : confirmed ? '작성 완료' : '작성 중'}</span>}
      </div>
      {code && (
        <div className="notice no-print">정산 {code}의 건명·금액·날짜를 그대로 채웠어요. 금액과 날짜는 정산 건에서 가져오므로 여기서는 고칠 수 없어요.</div>
      )}

      {error && <div className="error no-print">{error}</div>}
      {busy === 'load' && <div className="empty">양식을 만드는 중…</div>}

      {form && saved && (
        <>
          <div className="card form-guide no-print">
            <FormLegend />
            {todo.length > 0 ? (
              <div className="form-todo">
                <b>직접 적어야 하는 칸 {todo.length}개</b>
                <span className="hint">누르면 그 칸으로 가요.</span>
                <div className="btn-row start">
                  {todo.map((c) => <button key={c.key} type="button" className="btn small" onClick={() => focusCell(c.key)}>{c.label}</button>)}
                </div>
              </div>
            ) : (
              <div className="form-todo done">
                <b>적어야 하는 칸을 모두 채웠어요.</b>
                <span className="hint">내용을 읽고 아래에서 확인 표시를 한 뒤 관리자에게 보내세요.</span>
              </div>
            )}
          </div>

          <FormSheet form={form} fields={fields} onEdit={edit} />

          {note && <div className="doc-note no-print">{note}</div>}

          <div className="card form-actions no-print">
            <div className="btn-row">
              <button type="button" className="btn" disabled={Boolean(busy)} onClick={fill}>{busy === 'fill' ? 'AI가 쓰는 중…' : 'AI 제안 다시 받기'}</button>
              <button type="button" className="btn" disabled={Boolean(busy) || !dirty} onClick={save}>{busy === 'save' ? '저장 중…' : '저장'}</button>
              <button type="button" className="btn" onClick={() => window.print()}>인쇄 · PDF 저장</button>
            </div>
            <label className="check-inline doc-confirm">
              <input type="checkbox" checked={confirmed} disabled={Boolean(busy) || todo.length > 0} onChange={(e) => toggleConfirm(e.target.checked)} />
              <span>내용을 직접 읽고 확인했습니다.{todo.length > 0 && ' (빈 칸을 먼저 채워 주세요)'}</span>
            </label>
            <div className="btn-row between">
              <span className="hint">
                {sent ? `${when(saved.sent_at)}에 보냈어요. 내용을 고치면 다시 보내야 해요.` : '보내면 관리자 화면의 이 정산 건에 증빙 서류로 붙어요.'}
              </span>
              <button type="button" className="btn primary" disabled={Boolean(busy) || !confirmed || Boolean(sent)} onClick={send}>
                {busy === 'send' ? '보내는 중…' : sent ? '보냄' : '관리자에게 보내기'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
