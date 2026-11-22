// 출장 신청(GET /api/trips) 응답을 화면에 보일 때 쓰는 작은 도구들.

/** '2026-12-03' 또는 '2026-12-03 ~ 2026-12-04' (당일 출장이면 날짜 하나) */
export function periodText(start, end) {
  if (!start) return ''
  return !end || start === end ? start : `${start} ~ ${end}`
}

// 진행 단계 → 배지 색 (index.css .badge.good / .warn / .muted)
export const STAGE_TONE = {
  '출장 예정': 'muted',
  '출장 중': 'warn',
  '정산 전': 'bad',
  '정산 제출': 'good',
}

/** 아직 정산하지 않은 출장 = 출장 정산에서 불러올 수 있는 것 */
export const settleable = (trip) => !trip.submission && (trip.stage === '정산 전' || trip.stage === '출장 중')
