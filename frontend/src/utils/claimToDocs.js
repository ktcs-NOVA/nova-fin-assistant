// 정산 → 문서 작성 연결 (2026-11-13 코칭: 이미 입력한 금액·증빙·참석자가 문서에 반영되게).
// 청구 검증에서 입력한 내용(또는 이미 제출한 건)으로 서류 입력 칸을 미리 채웁니다.
// 여기서 만드는 fields 의 키는 components/DocumentEditor.jsx 의 DOC_SCHEMA 와 같아야 합니다.
// 사람이 써야 하는 칸(논의 내용, 출장 목적·수행 내용)은 비워 둡니다 — 초안은 그 뒤 "초안 만들기"로.

import { CLAIM } from './claimTypes.js'

const REGION_GROUPS = ['광역시', '기타']   // 숙박비 상한용 지역 구분이라 출장지 이름으로 쓰지 않음
const sum = (items, test) => items.filter((it) => test(String(it.field ?? ''))).reduce((n, it) => n + (Number(it.amount) || 0), 0)
const isTransport = (f) => /교통|운임|철도|KTX|SRT|항공|버스|택시|통행료|주유|유류|자가용|주차/.test(f)

/** 검증 요청(claim) 또는 제출 건(submission) → 공통 모양 */
function normalize(src) {
  const items = src.expenses ?? src.items ?? []
  const first = items[0] ?? {}
  const dates = items.map((it) => it.date).filter(Boolean).sort()
  return {
    type: src.trip_type ?? src.type ?? '',
    code: src.id ?? null,                       // 제출 번호 (제출 전이면 없음)
    trip: src.trip ?? {},
    items,
    total: src.amount ?? items.reduce((n, it) => n + (Number(it.amount) || 0), 0),
    firstDate: dates[0] ?? '',
    lastDate: dates[dates.length - 1] ?? '',
    merchant: first.merchant ?? src.merchant ?? '',
    attendees: Array.isArray(first.attendees) ? first.attendees : [],
    meetingPurpose: first.meeting_purpose ?? '',
  }
}

/**
 * 이 정산에 이어서 쓸 서류 목록: [{ kind, label, fields, origin }]
 * src 는 청구 검증 요청(claim) 이거나 제출 건(목록·상세 응답). user 는 로그인한 사람.
 */
export function docsForClaim(src, user) {
  const c = normalize(src)
  const origin = c.code ? `정산 ${c.code}` : '청구 검증'

  if (c.type === CLAIM.MEETING) {
    return [{
      kind: '회의록',
      label: '회의록 초안 쓰기',
      origin,
      fields: {
        meeting_title: c.meetingPurpose,
        meeting_date: c.firstDate,
        place: c.merchant,
        attendees: c.attendees,
        receipt_amount: c.total || undefined,
      },
    }]
  }

  if (c.type.includes('출장')) {
    const start = c.trip.start_date ?? c.firstDate
    const end = c.trip.end_date ?? c.lastDate
    const region = c.trip.destination ?? c.trip.region ?? ''
    const destination = REGION_GROUPS.includes(region) ? '' : region
    const fees = {
      transport_fee: sum(c.items, isTransport),
      lodging_fee: sum(c.items, (f) => f.includes('숙박')),
      daily_fee: sum(c.items, (f) => f.includes('일비')),
      meal_fee: sum(c.items, (f) => f.includes('식비')),
    }
    for (const k of Object.keys(fees)) if (!fees[k]) delete fees[k]
    return [
      { kind: '출장보고서', label: '출장보고서 쓰기', origin, fields: { trip_start: start, trip_end: end, destination, ...fees } },
      { kind: '출장원', label: '출장원 쓰기', origin, fields: { trip_start: start, trip_end: end, destination, total_amount: c.total || undefined, signer_name: user?.name ?? '' } },
    ]
  }

  return []   // 기타 법인카드: 이어 쓸 서류 종류가 아직 없음
}
