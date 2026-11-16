// 내 정산 현황: 내가 제출한 건과 AI 판정·검토 상태를 한눈에 봅니다. (listMySubmissions, 로그인한 사번 기준)
// 반려된 건은 사유가 펼쳐진 카드(RejectedCard)로 보이고, 거기서 바로 고쳐서 다시 제출할 수 있습니다 (U-09).

import { useEffect, useState } from 'react'
import { listMySubmissions, STATUS } from '../api/client.js'
import VerdictBadge from '../components/VerdictBadge.jsx'
import StatusTag from '../components/StatusTag.jsx'
import NextDocs from '../components/NextDocs.jsx'
import LedgerButton from '../components/LedgerButton.jsx'
import RejectedCard from '../components/RejectedCard.jsx'
import Icon from '../components/Icons.jsx'

const won = (n) => Number(n).toLocaleString('ko-KR') + '원'

export default function MyStatusPage({ user, onNavigate, onSendToVerify }) {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false
    listMySubmissions()
      .then((d) => { if (!ignore) setRows(d.items ?? []) })
      .catch((e) => { if (!ignore) setError(e.message) })
    return () => { ignore = true }
  }, [])

  // 반려됐는데 아직 고쳐서 다시 내지 않은 건
  const toFix = (rows ?? []).filter((s) => s.status === STATUS.REJECTED && !s.resubmitted_as).length

  return (
    <div>
      <div className="page-title">
        <h1>내 정산 현황</h1>
        <span className="desc">제출한 정산과 검토 상태</span>
        {/* 내 정산 건의 지출 항목을 한 줄씩 정리한 엑셀 (반려된 건 제외) */}
        {rows?.length > 0 && <LedgerButton />}
      </div>
      {error && <div className="empty" role="alert">{error}</div>}
      {!error && rows === null && <div className="empty">불러오는 중…</div>}
      {rows && rows.length === 0 && <div className="empty">아직 제출한 정산이 없어요.</div>}
      {toFix > 0 && (
        <div className="reject-banner" role="status">
          <Icon name="warn" size={18} />
          <span>반려된 정산이 <b>{toFix}건</b> 있어요. 사유를 확인하고 고쳐서 다시 제출해 주세요.</span>
        </div>
      )}
      {rows && rows.length > 0 && (
        <ul className="recent-list">
          {rows.map((s) => s.status === STATUS.REJECTED ? (
            <RejectedCard key={s.id} sub={s} user={user} onNavigate={onNavigate} onSendToVerify={onSendToVerify} />
          ) : (
            <li key={s.id}>
              <div>
                <div className="recent-name">{s.type} · {s.purpose}</div>
                <div className="hint">{s.date} · {won(s.amount)} · {s.id}</div>
                {/* 이 정산의 내용으로 채운 서류 쓰기 (회의비 → 회의록, 출장 → 출장보고서·출장원) */}
                <NextDocs compact src={s} user={user} onNavigate={onNavigate} />
              </div>
              <span className="row-badges"><VerdictBadge verdict={s.verdict} /><StatusTag status={s.status} /></span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
