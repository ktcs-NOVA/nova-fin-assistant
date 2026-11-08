// 근거 상태 표시 (U-03)
// 근거를 찾았으면 "근거 조항 N개", 못 찾았으면 "담당자 확인 필요" 경고를 보여줍니다.
// AI 가 근거 없이 지어낸 답을 믿지 않도록, 근거가 없을 때는 눈에 띄게 표시합니다.

import { VERDICT } from '../api/client.js'

export default function GroundNotice({ grounded, count, contact }) {
  if (grounded) {
    return <span className="badge good">근거 조항 {count}개</span>
  }
  return (
    <div className="notice warn" role="status">
      <strong>{VERDICT.CHECK}</strong>
      <span>등록된 규정에서 근거를 찾지 못했습니다. 정확한 처리는 담당자에게 확인해 주세요.</span>
      {contact && (
        <span>
          담당: {contact.department} {contact.name}
          {contact.phone && ` · 연락처 ${contact.phone}`}
        </span>
      )}
    </div>
  )
}
