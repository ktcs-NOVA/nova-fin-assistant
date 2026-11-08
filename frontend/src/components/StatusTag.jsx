// 검토 상태 태그: 검토 대기 / 승인 / 반려
import { STATUS } from '../api/client.js'

const STYLE = {
  [STATUS.PENDING]: 'muted',
  [STATUS.APPROVED]: 'good',
  [STATUS.REJECTED]: 'bad',
}

export default function StatusTag({ status }) {
  return <span className={`badge ${STYLE[status] ?? 'muted'}`}>{status}</span>
}
