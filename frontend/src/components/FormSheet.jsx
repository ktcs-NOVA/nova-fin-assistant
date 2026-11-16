// 기본 양식(지출 결과서 + 검수확인서)을 원 양식 모양의 표로 그립니다.
// 양식의 칸 구성과 값은 백엔드(domains/documents/forms.py)가 정하고, 여기서는 그대로 그리기만 합니다.
// 칸마다 값이 어디서 왔는지 색으로 구분합니다: 자동 입력 / AI 제안 / 직접 입력 / 서명·날인.
//   fields + onEdit 를 주면 고칠 수 있는 칸이 입력창이 되고(직원), 안 주면 읽기 전용(관리자)입니다.

import { sourceOf } from '../utils/formCells.js'

const SOURCES = [
  { id: 'auto', label: '자동 입력', desc: '정산 건에서 가져온 값' },
  { id: 'ai', label: 'AI 제안', desc: '고칠 수 있어요' },
  { id: 'manual', label: '직접 입력', desc: '직접 적는 칸' },
  { id: 'blank', label: '서명·날인', desc: '인쇄한 뒤 채워요' },
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
  if (!cell.key) return cell.value   // 서명 칸(blank)은 비워 둠 — 인쇄한 뒤 채우는 자리
  const value = fields ? String(fields[cell.key] ?? '') : cell.value
  if (!onEdit) return value || <span className="muted-text">—</span>
  return (
    <textarea
      id={`cell-${cell.key}`}
      rows={value.length > 18 ? 2 : 1}
      className={`form-input${cell.required && !value.trim() ? ' need' : ''}`}
      value={value}
      placeholder={cell.placeholder ?? ''}
      aria-label={cell.label}
      maxLength={60}
      onChange={(e) => onEdit(cell.key, e.target.value.replace(/\n/g, ' '))}
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

function Sheet({ sheet, fields, onEdit }) {
  const cols = sheet.table.columns
  return (
    <div className="form-paper">
      <div className="form-title">{sheet.title}</div>

      <table className="form-table form-info">
        <tbody>
          {sheet.info.map((r) => (
            <tr key={r.label}><th scope="row">{r.label}</th><Td cell={r.cell} fields={fields} onEdit={onEdit} /></tr>
          ))}
        </tbody>
      </table>

      <table className="form-table">
        <colgroup>{cols.map((c) => <col key={c.label} style={{ width: c.width }} />)}</colgroup>
        <thead><tr>{cols.map((c) => <th key={c.label} scope="col">{c.label}</th>)}</tr></thead>
        <tbody>
          {sheet.table.rows.map((row, i) => (
            <tr key={i}>{row.map((cell, j) => <Td key={j} cell={cell} fields={fields} onEdit={onEdit} />)}</tr>
          ))}
          <tr className="form-total">
            <th scope="row" colSpan={cols.length - 1}>{sheet.table.total.label}</th>
            <td className="src-auto al-right">{sheet.table.total.value}</td>
          </tr>
          {(sheet.extra ?? []).map((x) => (
            <tr key={x.label}>
              <th scope="row" colSpan={2}>{x.label}</th>
              <Td cell={x.cell} fields={fields} onEdit={onEdit} colSpan={cols.length - 2} />
            </tr>
          ))}
        </tbody>
      </table>

      <p className="form-closing">{sheet.closing}</p>
      <p className="form-date">{sheet.date}</p>

      <table className="form-table form-signers">
        <tbody>
          {sheet.signers.map((s) => (
            <tr key={s.role}>
              <th scope="row">{s.role}</th>
              <Td cell={s.cell} fields={fields} onEdit={onEdit} />
              <td className="src-blank form-seal-cell"><span className="form-seal">(인)</span></td>
            </tr>
          ))}
        </tbody>
      </table>

      {sheet.footnote && <p className="form-footnote">{sheet.footnote}</p>}

      {sheet.evidence && (
        <>
          <div className="form-subtitle">검 수 증 빙</div>
          <table className="form-table form-evidence">
            <thead><tr><th scope="col">지출 날짜</th><th scope="col">구분 / 품명</th><th scope="col">결제</th><th scope="col">금액</th><th scope="col">증빙 사진</th></tr></thead>
            <tbody>
              {sheet.evidence.map((ev, i) => (
                <tr key={i}>
                  <td className="src-auto al-center">{ev.date}</td>
                  <td className="src-auto">{ev.label}</td>
                  <td className="src-auto al-center">{ev.payment}</td>
                  <td className="src-auto al-right">{ev.amount}</td>
                  <td className="src-blank al-center"><span className="muted-text">영수증·카드 전표 첨부</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}

export default function FormSheet({ form, fields, onEdit }) {
  return (
    <div className="form-sheets">
      {form.sheets.map((sh) => <Sheet key={sh.title} sheet={sh} fields={fields} onEdit={onEdit} />)}
    </div>
  )
}
