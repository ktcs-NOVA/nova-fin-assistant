// 반려된 정산 건 → 청구 검증 화면의 초기값. "고쳐서 다시 제출"을 누르면 같은 내용이 채워진 채로 열립니다.
// resubmit 에 원래 제출 번호·건명·계정과목을 실어 두면 제출 패널이 그 건의 재제출로 보냅니다 (백엔드 resubmit_of).

import { CLAIM } from './claimTypes.js'

const KNOWN = Object.values(CLAIM)

export function resubmitPrefill(sub, user) {
  // 예전 유형 이름(법인카드·업무추진비)으로 낸 건은 지금의 세 유형에 맞춤
  const type = KNOWN.includes(sub.type) ? sub.type : String(sub.type).includes('출장') ? CLAIM.TRIP : CLAIM.CARD
  const first = sub.expenses?.[0] ?? {}
  const trip = {}
  for (const k of ['start_date', 'end_date', 'region', 'vehicle']) if (sub.trip?.[k]) trip[k] = sub.trip[k]
  return {
    from: 'resubmit',
    trip_type: type,
    grade: user?.grade ?? '직원 3급 이하',
    trip,
    items: (sub.expenses ?? []).map((e) => ({
      field: e.field ?? '',
      amount: String(e.amount ?? ''),
      date: e.date ?? '',
      note: e.note ?? '',
      nights: e.nights ? String(e.nights) : '',
      breakfast_included: Boolean(e.breakfast_included),
      seat_class: e.seat_class ?? '',
      exception_reason: e.exception_reason ?? '',
      merchant: e.merchant ?? '',
      merchant_type: e.merchant_type ?? '',
      time: e.time ?? '',
      payment: e.payment ?? '',
      receipt_file: e.merchant ? 'receipt' : '',   // 영수증에서 온 항목 표시(가맹점·시각·결제수단을 그대로 실어 보냄)
      receipt_id: e.receipt_id ?? '',
    })),
    meeting: {
      purpose: first.meeting_purpose ?? '',
      attendees: (first.attendees ?? []).join(', '),
      count: first.participant_count ? String(first.participant_count) : '',
      external: first.category === 'business',
      pre_approved: Boolean(first.pre_approved),
      daily_audit: Boolean(first.daily_audit),
    },
    resubmit: { of: sub.id, purpose: sub.purpose ?? '', account: sub.account ?? '' },
  }
}
