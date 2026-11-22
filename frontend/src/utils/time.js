// 시각 문자열 도구. 저장·전송은 'HH:MM' 24시간제, 화면은 '오전 9:30 / 오후 2:30' 12시간제.

/** 'HH:MM' → 자정부터 분. 비었으면 null */
export const toMin = (hhmm) => (hhmm ? Number(String(hhmm).slice(0, 2)) * 60 + Number(String(hhmm).slice(3, 5)) : null)

/** 분 → 'HH:MM' */
export const toHHMM = (m) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`

/** 'HH:MM' (또는 'HH:MM:SS') → '오전 9:30'. 비었으면 '' */
export function formatTime(hhmm) {
  const m = toMin(hhmm)
  if (m == null) return ''
  const h = Math.floor(m / 60)
  return `${h < 12 ? '오전' : '오후'} ${h % 12 || 12}:${String(m % 60).padStart(2, '0')}`
}
