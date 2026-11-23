// 정산 유형 (2026-11-13 코칭: "국내 출장 / 회의비 / 기타 법인카드 사용" 세 가지. 점심·회식은 회의비에 합침)
// 여기 값이 청구 검증 요청의 trip_type 으로 그대로 가고, 제출 건의 "유형"으로 관리자 화면에 보입니다.
// 백엔드 엔진은 이름에 "출장" 이 들어 있는지만 보므로 새 이름을 써도 규칙은 그대로 적용됩니다.

export const CLAIM = { TRIP: '국내출장', LOCAL_TRIP: '근무지 내 출장', MEETING: '회의비', CARD: '기타 법인카드' }

// 회의비 안의 구분 (항목명으로 들어감)
export const MEETING_FIELDS = ['회의 식대', '다과비', '기타 회의 경비']

/** 영수증 업종으로 회의비 구분을 추정 (카페·베이커리면 다과비, 아니면 식대) */
export function guessMeetingField(businessType = '') {
  return /카페|커피|베이커리|제과|디저트|다과/.test(businessType) ? MEETING_FIELDS[1] : MEETING_FIELDS[0]
}

// 참석자 한 명은 { name, team } 으로 입력받고, 저장·전송할 때는 "이름 (소속)" 한 줄로 만듭니다.
// (백엔드 documents/forms.py 의 _split_person 이 같은 규칙으로 다시 나눕니다.)
export const emptyPerson = () => ({ name: '', team: '' })

/** { name: '홍길동', team: '해운정책팀' } → "홍길동 (해운정책팀)". 소속이 없으면 이름만. */
export function joinPerson({ name = '', team = '' } = {}) {
  const n = name.trim().replace(/[()]/g, ' ').replace(/\s+/g, ' ').trim()
  const t = team.trim().replace(/[()]/g, ' ').replace(/\s+/g, ' ').trim()
  return n && t ? `${n} (${t})` : n
}

/** "홍길동 (해운정책팀)" → { name, team }. 예전에 적던 "해운정책팀 홍길동" 도 읽습니다 (첫 낱말이 소속). */
export function parsePerson(text = '') {
  const s = String(text).trim()
  const m = s.match(/^(.*?)\s*\(([^()]+)\)$/)
  if (m && m[1].trim()) return { name: m[1].trim(), team: m[2].trim() }
  const parts = s.split(/\s+/).filter(Boolean)
  return parts.length > 1 ? { name: parts.slice(1).join(' '), team: parts[0] } : { name: parts[0] ?? '', team: '' }
}

/** 입력한 참석자 줄 → 저장할 문자열 목록 (이름이 빈 줄은 뺌) */
export function peopleToAttendees(people = []) {
  return people.map(joinPerson).filter(Boolean)
}

/** 이름·소속이 모두 같은 참석자가 있으면 그 이름 (없으면 '') — 동명이인은 소속으로 구분해야 함 */
export function duplicatePerson(people = []) {
  const seen = new Set()
  for (const p of people) {
    const key = joinPerson(p)
    if (!key) continue
    if (seen.has(key)) return p.name.trim()
    seen.add(key)
  }
  return ''
}

/** "홍길동, 김철수 / 이영희" 처럼 적은 참석자를 목록으로 */
export function splitAttendees(text = '') {
  return text.split(/[,\n/]/).map((s) => s.trim()).filter(Boolean)
}
