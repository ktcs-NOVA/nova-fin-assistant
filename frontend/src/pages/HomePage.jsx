// 직원 홈: "무엇을 하시겠어요?" 큰 타일 3개 + 최근 정산.
// 내 제출 내역(listMySubmissions)으로 보완 알림과 건수를 채웁니다. 목업 모드에서는 예시 데이터예요.

import { useEffect, useState } from 'react'
import { listDocuments, listMySubmissions, USE_MOCK, VERDICT } from '../api/client.js'
import VerdictBadge from '../components/VerdictBadge.jsx'

const shortDate = (d) => {
  const t = new Date(d)
  return Number.isNaN(t.getTime()) ? d : `${t.getMonth() + 1}월 ${t.getDate()}일`
}

export default function HomePage({ user, onNavigate }) {
  const [rows, setRows] = useState(null)   // null = 불러오는 중
  const [workingDocs, setWorkingDocs] = useState(null)   // 작성 중인 서류 수

  useEffect(() => {
    let ignore = false
    listMySubmissions()
      .then((d) => { if (!ignore) setRows(d.items ?? []) })
      .catch(() => { if (!ignore) setRows([]) })
    return () => { ignore = true }
  }, [])

  useEffect(() => {
    let ignore = false
    listDocuments()
      .then((d) => { if (!ignore) setWorkingDocs(d.filter((x) => x.status !== '작성 완료').length) })
      .catch(() => { if (!ignore) setWorkingDocs(0) })
    return () => { ignore = true }
  }, [])

  const mine = rows ?? []
  const fixCount = mine.filter((s) => s.verdict === VERDICT.FIX).length
  const pendingCount = mine.filter((s) => s.status === '검토 대기').length
  const recent = [...mine].sort((a, b) => String(b.submitted_at ?? b.date).localeCompare(String(a.submitted_at ?? a.date))).slice(0, 3)

  return (
    <div className="home">
      <h1>{user.name} 님, 무엇을 하시겠어요?</h1>
      <p className="hint">아래에서 하나를 고르면 다음 단계로 안내해 드려요.</p>

      {fixCount > 0 && (
        <button type="button" className="notice-bar" onClick={() => onNavigate('mystatus')}>
          <span><b>보완이 필요한 정산 {fixCount}건</b>이 있어요. 내용을 확인해 주세요.</span>
          <span className="notice-go">확인하기 →</span>
        </button>
      )}

      <div className="tile-grid hero">
        <button type="button" className="tile primary" onClick={() => onNavigate('type')}>
          <span className="tile-title">정산하기</span>
          <span className="tile-desc">출장, 식대, 회의비 등 사용 내역을 제출하기 전에 규정에 맞는지 확인하고 서류를 준비해요.</span>
          <span className="tile-go">시작하기 →</span>
        </button>
        <button type="button" className="tile" onClick={() => onNavigate('mystatus')}>
          <span className="tile-title">내 정산 현황</span>
          <span className="tile-desc">제출한 정산과 반려·보완 요청을 한눈에 확인해요.</span>
          <span className="tile-go">{rows === null ? '불러오는 중…' : `검토 대기 ${pendingCount}건 · 보완 ${fixCount}건`}</span>
        </button>
        <button type="button" className="tile" onClick={() => onNavigate('checklist')}>
          <span className="tile-title">문서 작업</span>
          <span className="tile-desc">출장보고서·회의록·출장원을 쓰다 말아도 저장해 두고, 이어서 써요.</span>
          <span className="tile-go">{workingDocs ? `이어서 쓰기 ${workingDocs}건 →` : '열기 →'}</span>
        </button>
      </div>

      <h2 className="home-sub">최근 정산 {USE_MOCK && recent.length > 0 && <span className="hint">(예시 데이터)</span>}</h2>
      {rows === null ? (
        <div className="empty">불러오는 중…</div>
      ) : recent.length === 0 ? (
        <div className="empty">아직 제출한 정산이 없어요. “정산하기”로 시작해 보세요.</div>
      ) : (
        <ul className="recent-list">
          {recent.map((s) => (
            <li key={s.id}>
              <div>
                <div className="recent-name">{s.type} · {s.purpose}</div>
                <div className="hint">{shortDate(s.submitted_at ?? s.date)}</div>
              </div>
              <VerdictBadge verdict={s.verdict} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
