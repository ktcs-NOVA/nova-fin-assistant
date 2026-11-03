// 검증 결과 전체: 종합 판정 요약 + 항목별 카드 목록
// 데이터 모양은 조율 문서 3-2 의 응답 전체와 같습니다.

import { VERDICT } from '../api/client.js'
import VerdictBadge from './VerdictBadge.jsx'
import ResultCard from './ResultCard.jsx'

export default function VerifyResult({ result }) {
  const { overall, items = [] } = result
  const count = (v) => items.filter((i) => i.verdict === v).length

  return (
    <div className="result">
      <div className="result-summary">
        <div>
          <span className="label">종합 판정</span>
          <VerdictBadge verdict={overall} />
        </div>
        <div className="result-counts">
          <span className="good">확인 가능 {count(VERDICT.OK)}</span>
          <span className="bad">보완 필요 {count(VERDICT.FIX)}</span>
          <span className="warn">담당자 확인 {count(VERDICT.CHECK)}</span>
        </div>
      </div>

      <div className="result-list">
        {items.map((item, i) => (
          <ResultCard key={`${item.field}-${i}`} item={item} />
        ))}
      </div>
    </div>
  )
}
