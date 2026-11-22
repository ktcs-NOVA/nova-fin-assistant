// 근거 미리보기 (U-03): 답변의 [1] 이나 근거 조항에 마우스를 올리면(휴대폰은 탭) 뜨는 작은 창.
// 조문은 본문 그대로, 별표는 표로 그리고 답변에 나온 행(예: 직원 3급 이하)을 강조합니다.

import { parseTable, relatedRows } from '../utils/excerpt.js'

export function TableView({ table, highlight }) {
  return (
    <>
      {table.before.map((line) => (
        <p key={line} className="peek-caption">{line}</p>
      ))}
      <div className="peek-table-wrap">
        <table className="peek-table">
          <thead>
            <tr>
              {table.headers.map((h) => (
                <th key={h} scope="col">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, i) => (
              <tr key={i} className={highlight.has(i) ? 'hit' : undefined}>
                {table.headers.map((h, j) =>
                  j === 0 ? (
                    <th key={h} scope="row">{row[h] ?? ''}</th>
                  ) : (
                    <td key={h}>{row[h] ?? ''}</td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.after.map((line) => (
        <p key={line} className="peek-note">{line}</p>
      ))}
    </>
  )
}

export default function SourcePeek({ source, answer, style, onEnter, onLeave, onClose }) {
  const table = source.chunk_type === 'table' ? parseTable(source.excerpt) : null
  const highlight = table ? relatedRows(table, answer) : new Set()

  return (
    <div
      className="peek"
      style={style}
      role="dialog"
      aria-label={`${source.regulation} ${source.article} 본문`}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      <div className="peek-head">
        <span className="source-ref">{source.ref}</span>
        <strong>
          {source.regulation} {source.article}
        </strong>
        {source.revised_at && <span className="source-date">개정 {source.revised_at}</span>}
        <button type="button" className="peek-close" onClick={onClose} aria-label="닫기">
          ×
        </button>
      </div>
      <div className="peek-body">
        {table ? (
          <>
            <TableView table={table} highlight={highlight} />
            {highlight.size > 0 && <p className="peek-hint">색칠한 줄이 답변에 쓰인 기준이에요.</p>}
          </>
        ) : (
          <p className="peek-text">{source.excerpt}</p>
        )}
      </div>
    </div>
  )
}
