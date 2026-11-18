// 출처 조항 본문(excerpt)을 화면에 보여 주기 좋게 나눕니다 (U-03 근거 미리보기).
//
// 별표는 백엔드에서 한 행이 한 줄로 저장돼 있습니다.
//   구분: 직원(3급 이하) | 일비(1일당): 30 | 식비(1일당): 27 | 숙박비(1일당): 서울 100 / 광역시 90 / 기타 80
// 이 줄들을 표(열 제목 + 행)로 되돌리고, 표가 아닌 줄은 위(제목·단위)와 아래(주석)로 나눕니다.

const FIELD_SEP = ' | '

// '구분: 직원(3급 이하) | 식비(1일당): 27' → [['구분', '직원(3급 이하)'], ['식비(1일당)', '27']]
function parseRow(line) {
  if (!line.includes(FIELD_SEP)) return null
  const fields = line.split(FIELD_SEP).map((part) => {
    const i = part.indexOf(': ')
    return i > 0 ? [part.slice(0, i).trim(), part.slice(i + 2).trim()] : null
  })
  return fields.every(Boolean) ? fields : null
}

// '[별표 1] 국내여비지급표 <개정 2020. 1. 15., …>' → '[별표 1] 국내여비지급표'
const tidyTitle = (line) => line.replace(/\s*<개정[^>]*>\s*/g, ' ').trim()

export function parseTable(excerpt) {
  const before = []
  const after = []
  const rows = []
  const headers = []
  for (const raw of excerpt.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    const fields = parseRow(line)
    if (!fields) {
      ;(rows.length ? after : before).push(tidyTitle(line))
      continue
    }
    const row = {}
    for (const [key, value] of fields) {
      if (!headers.includes(key)) headers.push(key)
      row[key] = value
    }
    rows.push(row)
  }
  if (rows.length < 2) return null // 표로 보기 어려우면 글로 보여 줌
  // '[별표 1] 국내여비지급표' 다음 줄의 '국내여비지급표' 처럼 다른 줄에 이미 있는 제목은 뺌
  const titles = [...new Set(before)].filter((t, i, all) => !all.some((o, j) => j !== i && o.includes(t)))
  return { before: titles, headers, rows, after }
}

// 답변에 나온 말로 관련 행을 찾습니다. 행 이름(첫 칸)의 낱말 중 다른 행에는 잘 없는 낱말
// (예: '3급', '1·2급', '사장')이 답변에 많이 나온 행을 강조합니다. 가장 많이 맞은 행만 고릅니다.
// '직원(3급 이하)' 답변이면 '직원'만 맞는 '직원(1·2급)' 행보다 '3급'까지 맞는 행이 앞섭니다.
export function relatedRows(table, text) {
  if (!table || !text) return new Set()
  const first = table.headers[0]
  const labels = table.rows.map((r) => r[first] || '')
  const words = labels.map((label) => [...new Set(label.match(/[가-힣A-Za-z0-9·]+/g) || [])])
  const count = new Map()
  words.flat().forEach((w) => count.set(w, (count.get(w) || 0) + 1))
  const rare = (w) => w.length >= 2 && count.get(w) <= labels.length / 2
  const scores = words.map((ws) => ws.filter((w) => rare(w) && text.includes(w)).length)
  const best = Math.max(0, ...scores)
  if (!best) return new Set()
  const hit = new Set(scores.flatMap((s, i) => (s === best ? [i] : [])))
  return hit.size === labels.length ? new Set() : hit // 전부 맞으면 강조할 의미가 없음
}
