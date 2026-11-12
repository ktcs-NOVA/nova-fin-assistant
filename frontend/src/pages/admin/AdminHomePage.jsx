// 관리자 홈: 오늘 검토할 정산 건수와 바로가기. 건수는 제출 목록(listSubmissions)에서 셉니다.
// "보완 요청 중" 상태는 아직 백엔드 상태값(검토 대기/승인/반려)에 없어서 타일에서 뺐어요.

import { useEffect, useState } from 'react'
import { listSubmissions, STATUS, VERDICT } from '../../api/client.js'
import VerdictBadge from '../../components/VerdictBadge.jsx'

export default function AdminHomePage({ user, onNavigate }) {
  const [rows, setRows] = useState(null)

  useEffect(() => {
    let ignore = false
    listSubmissions()
      .then((d) => { if (!ignore) setRows(d.items ?? []) })
      .catch(() => { if (!ignore) setRows([]) })
    return () => { ignore = true }
  }, [])

  const all = rows ?? []
  const pending = all.filter((s) => s.status === STATUS.PENDING)
  const needCheck = pending.filter((s) => s.verdict !== VERDICT.OK).length
  const approved = all.filter((s) => s.status === STATUS.APPROVED).length
  const preview = pending.slice(0, 3)

  return (
    <div className="home">
      <h1>{rows === null ? `${user.name} 님, 안녕하세요` : `${user.name} 님, 오늘 검토할 정산이 ${pending.length}건 있어요`}</h1>
      <p className="hint">AI가 먼저 점검한 결과를 보고, 승인 여부는 담당자가 결정해요.</p>

      <div className="tile-grid two">
        <button type="button" className="tile primary" onClick={() => onNavigate('review')}>
          <span className="tile-title">검토 대기</span>
          <span className="tile-desc">새로 제출된 정산이에요. AI 판정이 함께 보여요.</span>
          <span className="tile-go">{rows === null ? '불러오는 중…' : `${pending.length}건 · 확인 필요 ${needCheck}건`}</span>
        </button>
        <button type="button" className="tile" onClick={() => onNavigate('review')}>
          <span className="tile-title">승인 완료</span>
          <span className="tile-desc">승인된 정산 내역을 확인해요.</span>
          <span className="tile-go">{rows === null ? '불러오는 중…' : `${approved}건`}</span>
        </button>
        <button type="button" className="tile" onClick={() => onNavigate('qa')}>
          <span className="tile-title">규정 물어보기</span>
          <span className="tile-desc">판정이 헷갈릴 때 근거 조항을 찾아봐요.</span>
          <span className="tile-go">질문하기 →</span>
        </button>
      </div>

      {preview.length > 0 && (
        <>
          <h2 className="home-sub">검토 대기 목록</h2>
          <ul className="recent-list">
            {preview.map((s) => (
              <li key={s.id}>
                <button type="button" className="recent-link" onClick={() => onNavigate('review')}>
                  <span className="recent-name">{s.submitter}</span>
                  <span className="hint">{s.type} · {s.purpose} · {s.date}</span>
                </button>
                <VerdictBadge verdict={s.verdict} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
