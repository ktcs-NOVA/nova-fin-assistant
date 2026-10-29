// 판정 3단계 뱃지. 값은 client.js 의 VERDICT 세 가지 중 하나입니다.

import { VERDICT } from '../api/client.js'

const STYLE = {
  [VERDICT.OK]: 'good',
  [VERDICT.FIX]: 'bad',
  [VERDICT.CHECK]: 'warn',
}

export default function VerdictBadge({ verdict }) {
  const cls = STYLE[verdict] ?? 'muted'
  return <span className={`badge ${cls}`}>{verdict}</span>
}
