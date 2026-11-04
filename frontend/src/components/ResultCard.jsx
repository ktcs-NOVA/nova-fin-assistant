// 검증 결과 카드 한 장: 항목명 + 판정 + 메시지 + 근거 조항 + 수정 방법
// 데이터 모양은 조율 문서 3-2 의 items[] 한 개와 같습니다.

import VerdictBadge from './VerdictBadge.jsx'

export default function ResultCard({ item }) {
  const { field, verdict, message, basis, fix } = item
  return (
    <article className="result-card">
      <header className="result-head">
        <h3>{field}</h3>
        <VerdictBadge verdict={verdict} />
      </header>
      <p className="result-message">{message}</p>
      <dl className="result-meta">
        {basis && (
          <>
            <dt>근거</dt>
            <dd>{basis}</dd>
          </>
        )}
        {fix && (
          <>
            <dt>수정</dt>
            <dd>{fix}</dd>
          </>
        )}
      </dl>
    </article>
  )
}
