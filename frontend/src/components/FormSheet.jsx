// 기본 양식(지출 결과서 + 검수확인서 · 회의록 · 출장보고서)을 원 양식 모양의 표로 그립니다.
// 양식의 칸 구성과 값은 백엔드(domains/documents/forms.py)가 정하고, 여기서는 그대로 그리기만 합니다.
// 칸마다 값이 어디서 왔는지 색으로 구분합니다: 자동 입력 / AI 작성 / 직접 입력 / 서명·사진.
//   fields + onEdit 를 주면 고칠 수 있는 칸이 입력창이 되고(직원), 안 주면 읽기 전용(관리자)입니다.

import { useEffect, useState } from 'react'
import { getReceiptImageUrl } from '../api/client.js'
import { sourceOf } from '../utils/formCells.js'

const SOURCES = [
  { id: 'auto', label: '자동 입력', desc: '정산 건에서 가져온 값' },
  { id: 'ai', label: 'AI 작성', desc: '고칠 수 있어요' },
  { id: 'manual', label: '직접 입력', desc: '직접 적는 칸' },
  { id: 'blank', label: '서명·사진', desc: '인쇄한 뒤 채워요' },
]

export function FormLegend() {
  return (
    <ul className="form-legend">
      {SOURCES.map((s) => (
        <li key={s.id}><span className={`form-chip src-${s.id}`}>{s.label}</span><span className="hint">{s.desc}</span></li>
      ))}
    </ul>
  )
}

function Cell({ cell, fields, onEdit }) {
  if (!cell.key) return cell.value   // 고칠 수 없는 칸 (서명 칸은 '(인)' 또는 빈 칸)
  const value = fields ? String(fields[cell.key] ?? '') : cell.value
  if (!onEdit) return value ? <span className="form-text">{value}</span> : <span className="muted-text">—</span>
  return (
    <textarea
      id={`cell-${cell.key}`}
      rows={cell.multiline ? 7 : value.length > 18 ? 2 : 1}
      className={`form-input${cell.multiline ? ' multi' : ''}${cell.required && !value.trim() ? ' need' : ''}`}
      value={value}
      placeholder={cell.placeholder ?? ''}
      aria-label={cell.label}
      maxLength={cell.limit ?? 60}
      onChange={(e) => onEdit(cell.key, cell.multiline ? e.target.value : e.target.value.replace(/\n/g, ' '))}
    />
  )
}

function Td({ cell, fields, onEdit, ...rest }) {
  const source = sourceOf(cell, onEdit ? fields : null)
  return (
    <td className={`src-${source}${cell.align ? ` al-${cell.align}` : ''}`} {...rest}>
      <Cell cell={cell} fields={fields} onEdit={onEdit} />
    </td>
  )
}

// 보관해 둔 영수증 사진. 로그인 토큰이 있어야 받을 수 있어서 직접 받아 온 뒤 그립니다.
function ReceiptPhoto({ id }) {
  const [url, setUrl] = useState('')
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let alive = true
    let made = ''
    getReceiptImageUrl(id)
      .then((u) => { made = u; if (alive) setUrl(u); else URL.revokeObjectURL(u) })
      .catch(() => { if (alive) setFailed(true) })
    return () => { alive = false; if (made) URL.revokeObjectURL(made) }
  }, [id])
  if (failed) return <span className="muted-text">사진을 불러오지 못했어요</span>
  return url ? <img className="form-receipt" src={url} alt="영수증 사진" /> : <span className="muted-text">불러오는 중…</span>
}

function Block({ block, fields, onEdit }) {
  const edit = { fields, onEdit }
  if (block.type === 'info') {
    return (
      <table className="form-table form-info">
        <tbody>
          {block.rows.map((r) => <tr key={r.label}><th scope="row">{r.label}</th><Td cell={r.cell} {...edit} /></tr>)}
        </tbody>
      </table>
    )
  }
  if (block.type === 'table') {
    const cols = block.columns
    return (
      <table className="form-table">
        {block.caption && <caption>{block.caption}</caption>}
        <colgroup>{cols.map((c, i) => <col key={i} style={{ width: c.width }} />)}</colgroup>
        <thead><tr>{cols.map((c, i) => <th key={i} scope="col">{c.label}</th>)}</tr></thead>
        <tbody>
          {block.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <Td key={j} cell={cell} {...edit} />)}</tr>)}
          {block.total && (
            <tr className="form-total">
              <th scope="row" colSpan={block.total.span}>{block.total.label}</th>
              <td className="src-auto al-right" colSpan={cols.length - block.total.span}>{block.total.value}</td>
            </tr>
          )}
        </tbody>
      </table>
    )
  }
  if (block.type === 'field') {
    return (
      <table className="form-table form-field">
        <tbody><tr><th scope="row">{block.label}</th><Td cell={block.cell} {...edit} /></tr></tbody>
      </table>
    )
  }
  if (block.type === 'note') return <p className={`form-note ${block.style}`}>{block.text}</p>
  if (block.type === 'signers') {
    return (
      <table className="form-table form-signers">
        <tbody>
          {block.rows.map((s) => (
            <tr key={s.role}>
              <th scope="row">{s.role}</th>
              <Td cell={s.cell} {...edit} />
              <td className="src-blank form-seal-cell"><span className="form-seal">(인)</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    )
  }
  if (block.type === 'evidence') {
    return (
      <>
        <div className="form-subtitle">{block.title}</div>
        <table className="form-table form-evidence">
          <thead><tr><th scope="col">지출 날짜</th><th scope="col">품명</th><th scope="col">결제</th><th scope="col">금액</th><th scope="col">증빙 사진</th></tr></thead>
          <tbody>
            {block.items.map((ev, i) => (
              <tr key={i}>
                <td className="src-auto al-center">{ev.date}</td>
                <td className="src-auto">{ev.label}</td>
                <td className="src-auto al-center">{ev.payment}</td>
                <td className="src-auto al-right">{ev.amount}</td>
                {ev.receipt_id
                  ? <td className="src-auto al-center"><ReceiptPhoto id={ev.receipt_id} /></td>
                  : <td className="src-blank al-center"><span className="muted-text">영수증·카드 전표 첨부</span></td>}
              </tr>
            ))}
          </tbody>
        </table>
      </>
    )
  }
  if (block.type === 'photos') {
    return (
      <table className="form-table form-photos">
        <tbody>
          <tr><th scope="row">{block.title}</th></tr>
          <tr><td className="src-blank al-center"><span className="muted-text">{block.hint}</span></td></tr>
        </tbody>
      </table>
    )
  }
  return null
}

// 결재란: 제목 오른쪽 위의 작은 표. 직위 아래 칸은 인쇄한 뒤 서명·날인합니다 (결재가 넘어가는 기능은 없음).
function ApprovalBox({ approval }) {
  return (
    <table className="form-table form-approval" aria-label="결재란">
      <tbody>
        <tr>
          <th scope="row" rowSpan={2} className="form-approval-label">{approval.label}</th>
          {approval.roles.map((r) => <th key={r} scope="col">{r}</th>)}
        </tr>
        <tr>{approval.roles.map((r) => <td key={r} className="src-blank" aria-label={`${r} 서명 칸`} />)}</tr>
      </tbody>
    </table>
  )
}

export default function FormSheet({ form, fields, onEdit }) {
  return (
    <div className="form-sheets">
      {form.sheets.map((sh) => (
        <div key={sh.title} className="form-paper">
          {sh.approval ? (
            <div className="form-head">
              <div className="form-title">{sh.title}</div>
              <ApprovalBox approval={sh.approval} />
            </div>
          ) : <div className="form-title">{sh.title}</div>}
          {sh.blocks.map((b, i) => <Block key={i} block={b} fields={fields} onEdit={onEdit} />)}
        </div>
      ))}
    </div>
  )
}
