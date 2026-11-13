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

/** "홍길동, 김철수 / 이영희" 처럼 적은 참석자를 목록으로 */
export function splitAttendees(text = '') {
  return text.split(/[,\n/]/).map((s) => s.trim()).filter(Boolean)
}
