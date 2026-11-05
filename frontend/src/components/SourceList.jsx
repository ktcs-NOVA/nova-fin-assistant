// 근거·출처 목록 (U-03): 답변이 참고한 규정 조항, 개정일, 원문 링크
// sources[] 한 개 모양: { ref, regulation, article, revised_at, url }
// activeRef 와 같은 번호의 항목을 강조합니다 (본문의 [1] 을 누르면 해당 출처가 강조됨).

export default function SourceList({ sources, activeRef, onSelect }) {
  if (!sources?.length) return null

  return (
    <div className="sources">
      <div className="sources-title">근거 조항</div>
      <ol className="source-list">
        {sources.map((s, i) => {
          const ref = s.ref ?? i + 1
          return (
            <li key={`${s.regulation}-${s.article}-${ref}`}>
              <button
                type="button"
                className={`source ${activeRef === ref ? 'on' : ''}`}
                onClick={() => onSelect?.(ref)}
              >
                <span className="source-ref">{ref}</span>
                <span className="source-name">
                  {s.regulation} {s.article}
                </span>
                {s.revised_at && <span className="source-date">개정 {s.revised_at}</span>}
              </button>
              {s.url && (
                <a className="source-link" href={s.url} target="_blank" rel="noreferrer">
                  원문 보기
                </a>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
