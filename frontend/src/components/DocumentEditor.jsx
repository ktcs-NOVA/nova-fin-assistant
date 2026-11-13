// 서류 한 건 작성 화면: 입력 → AI 초안 → 직접 읽고 확인 → 저장.
// 날짜·금액·참석자 같은 사실은 입력한 값으로만 채워지고, AI 는 메모 문장을 다듬기만 해요.
// 쓰다 만 채로 저장하면 목록의 "작성 중"에 남아 이어서 쓸 수 있어요.

import { useState } from 'react'
import { createDocument, draftDocument, updateDocument } from '../api/client.js'

// 종류별 입력 칸. type: text | date | number | list(쉼표로 구분) | area
export const DOC_SCHEMA = {
  출장보고서: {
    desc: '출장 기간·장소·수행 내용과 경비를 보고서로 정리해요.',
    fields: [
      { key: 'trip_start', label: '출장 시작일', type: 'date', required: true },
      { key: 'trip_end', label: '출장 종료일', type: 'date', required: true },
      { key: 'destination', label: '출장지', type: 'text', required: true, placeholder: '예) 부산 영도' },
      { key: 'purpose', label: '출장 목적', type: 'text', required: true, placeholder: '예) 부산지사 현장 점검', wide: true },
      { key: 'work_notes', label: '주요 수행 내용', type: 'area', required: true, placeholder: '한 일을 편하게 적어 주세요. 보고서 문장으로 다듬어 드려요.', wide: true },
      { key: 'transport_fee', label: '교통비(원)', type: 'number' },
      { key: 'lodging_fee', label: '숙박비(원)', type: 'number' },
      { key: 'daily_fee', label: '일비(원)', type: 'number' },
      { key: 'meal_fee', label: '식비(원)', type: 'number' },
    ],
  },
  회의록: {
    desc: '회의 정보와 논의 내용을 회의록으로 정리하고, 1인당 금액도 계산해요.',
    fields: [
      { key: 'meeting_title', label: '회의명', type: 'text', required: true, placeholder: '예) 주간 업무 회의', wide: true },
      { key: 'meeting_date', label: '회의 일시', type: 'date', required: true },
      { key: 'place', label: '장소', type: 'text' },
      { key: 'attendees', label: '참석자 (쉼표로 구분)', type: 'list', required: true, placeholder: '예) 노은비, 김철환, 이수정', wide: true },
      { key: 'receipt_amount', label: '회의 비용(원)', type: 'number' },
      { key: 'notes', label: '논의 내용 메모', type: 'area', required: true, placeholder: '논의한 내용을 편하게 적어 주세요.', wide: true },
    ],
  },
  출장원: {
    desc: '출장 정산에 붙이는 출장원 서식을 채워요.',
    fields: [
      { key: 'trip_start', label: '출장 시작일', type: 'date', required: true },
      { key: 'trip_end', label: '출장 종료일', type: 'date', required: true },
      { key: 'destination', label: '출장지', type: 'text', required: true },
      { key: 'purpose', label: '출장 목적', type: 'text', required: true, wide: true },
      { key: 'total_amount', label: '정산 금액(원)', type: 'number', required: true },
      { key: 'signer_name', label: '서명할 이름', type: 'text' },
    ],
  },
}

// 저장된 값 → 입력 칸에 보일 글자
function toForm(kind, fields) {
  const out = {}
  for (const f of DOC_SCHEMA[kind].fields) {
    const v = fields?.[f.key]
    out[f.key] = Array.isArray(v) ? v.join(', ') : v == null ? '' : String(v)
  }
  return out
}

// 입력 칸 → 저장할 값 (빈 칸은 보내지 않아요)
function toFields(kind, form) {
  const out = {}
  for (const f of DOC_SCHEMA[kind].fields) {
    const raw = (form[f.key] ?? '').trim()
    if (!raw) continue
    if (f.type === 'number') out[f.key] = Number(raw.replaceAll(',', '')) || 0
    else if (f.type === 'list') out[f.key] = raw.split(',').map((x) => x.trim()).filter(Boolean)
    else out[f.key] = raw
  }
  return out
}

export default function DocumentEditor({ doc, onBack, onChanged }) {
  const kind = doc.kind
  const schema = DOC_SCHEMA[kind]
  const [saved, setSaved] = useState(doc)            // 서버에 저장된 모습 (id 없으면 아직 저장 전)
  const [form, setForm] = useState(() => toForm(kind, doc.fields))
  const [draft, setDraft] = useState(doc.draft ?? '')
  const [confirmed, setConfirmed] = useState(Boolean(doc.confirmed))
  const [busy, setBusy] = useState('')               // '' | save | draft | confirm
  const [error, setError] = useState('')
  const [note, setNote] = useState('')

  const draftDirty = draft !== (saved.draft ?? '')

  // 입력값을 저장합니다. 처음이면 새로 만들고, 이미 있으면 고칩니다. 최신 서류를 돌려줘요.
  async function persist(extra = {}) {
    const fields = toFields(kind, form)
    const next = saved.id
      ? await updateDocument(saved.id, { fields, ...(draftDirty ? { draft } : {}), ...extra })
      : await createDocument({ kind, fields })
    setSaved(next)
    setConfirmed(next.confirmed)
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

  const save = () => run('save', () => persist(), '저장했어요. 나중에 “작성 중인 문서”에서 이어 쓸 수 있어요.')

  const makeDraft = () =>
    run('draft', async () => {
      const cur = await persist()
      const made = await draftDocument(cur.id)
      setSaved(made)
      setDraft(made.draft)
      setConfirmed(false)
      onChanged?.()
    }, '초안을 만들었어요. 내용을 읽고 고칠 곳이 있으면 직접 고쳐 주세요.')

  const toggleConfirm = (checked) =>
    run('confirm', async () => {
      if (checked) {
        const cur = await persist({ confirmed: true })
        setDraft(cur.draft)
      } else {
        const cur = await updateDocument(saved.id, { confirmed: false })
        setSaved(cur)
        setConfirmed(false)
        onChanged?.()
      }
    })

  async function copyDraft() {
    try {
      await navigator.clipboard.writeText(draft)
      setNote('초안을 복사했어요.')
    } catch {
      setNote('복사하지 못했어요. 글을 직접 선택해서 복사해 주세요.')
    }
  }

  return (
    <div className="doc-editor">
      <button type="button" className="btn small" onClick={onBack}>← 문서 목록</button>
      <div className="card-head doc-editor-head">
        <h2>{kind}{saved.id ? '' : ' 새로 쓰기'}</h2>
        {saved.id && <span className={`badge ${confirmed ? 'good' : 'muted'}`}>{confirmed ? '작성 완료' : '작성 중'}</span>}
      </div>
      {doc.origin && !saved.id && (
        <div className="notice">{doc.origin}에서 입력한 값을 채워 두었어요. 빈 칸만 적고 “초안 만들기”를 누르세요. 채워진 값도 고칠 수 있어요.</div>
      )}
      <p className="hint">{schema.desc} * 표시는 초안을 만들 때 꼭 필요해요.</p>

      <div className="card">
        <div className="doc-form">
          {schema.fields.map((f) => (
            <label key={f.key} className={`field ${f.wide ? 'field-wide' : ''}`}>
              <span className="field-label">{f.label}{f.required && <em>*</em>}</span>
              {f.type === 'area' ? (
                <textarea rows={4} value={form[f.key]} placeholder={f.placeholder}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
              ) : (
                <input type={f.type === 'date' ? 'date' : f.type === 'number' ? 'number' : 'text'} min={f.type === 'number' ? 0 : undefined}
                  value={form[f.key]} placeholder={f.placeholder}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
              )}
            </label>
          ))}
        </div>
        <div className="btn-row">
          <button type="button" className="btn" disabled={Boolean(busy)} onClick={save}>{busy === 'save' ? '저장 중…' : '저장하고 나중에 이어 쓰기'}</button>
          <button type="button" className="btn primary" disabled={Boolean(busy)} onClick={makeDraft}>{busy === 'draft' ? '초안 만드는 중…' : draft ? '초안 다시 만들기' : 'AI로 초안 만들기'}</button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {note && <div className="doc-note">{note}</div>}

      {draft && (
        <div className="card doc-draft">
          <div className="card-head">
            <h2>초안</h2>
            <button type="button" className="btn small" onClick={copyDraft}>복사하기</button>
          </div>
          <p className="hint">직접 고칠 수 있어요. 고치면 “확인” 표시가 풀리니 다시 읽고 체크해 주세요.</p>
          <textarea className="doc-draft-text" rows={16} value={draft} onChange={(e) => setDraft(e.target.value)} />
          <label className="check-inline doc-confirm">
            <input type="checkbox" checked={confirmed} disabled={Boolean(busy)} onChange={(e) => toggleConfirm(e.target.checked)} />
            <span>내용을 직접 읽고 확인했습니다.{draftDirty && ' (고친 내용도 함께 저장돼요)'}</span>
          </label>
          {draftDirty && (
            <div className="btn-row">
              <button type="button" className="btn small" disabled={Boolean(busy)} onClick={() => run('save', () => persist(), '고친 초안을 저장했어요.')}>고친 초안 저장</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
