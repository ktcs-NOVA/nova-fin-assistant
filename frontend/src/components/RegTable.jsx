// 별표(표)를 표로 그립니다. 근거 미리보기(SourcePeek)와 규정 원문 보기(RegulationViewer)가 함께 씁니다.
// table 은 utils/excerpt.js 의 parseTable 결과: { before, headers, rows, after }
// highlight: 강조할 행 번호 Set, query: 글자 강조할 검색어

import Marked from './Marked.jsx'

export default function RegTable({ table, highlight = new Set(), query = '' }) {
  return (
    <>
      {table.before.map((line) => (
        <p key={line} className="peek-caption"><Marked text={line} query={query} /></p>
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
                    <th key={h} scope="row"><Marked text={row[h] ?? ''} query={query} /></th>
                  ) : (
                    <td key={h}><Marked text={row[h] ?? ''} query={query} /></td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.after.map((line) => (
        <p key={line} className="peek-note"><Marked text={line} query={query} /></p>
      ))}
    </>
  )
}
