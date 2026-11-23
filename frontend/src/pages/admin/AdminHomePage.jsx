// 관리자 홈: 들어오자마자 제출 / 검토 대기 / 확인 필요 건수와, 확인이 필요한 건 목록이 바로 보입니다.
// (2026-11-13 코칭: 깊이 들어가야 보이면 안 되고 앞단에서 검토할 수 있어야 함. 반려는 확인 필요에 포함)
// 숫자·목록 기준은 검토 대기함과 같은 reviewQueue.js 를 씁니다. 숫자 카드나 행을 누르면 검토 대기함의 그 보기·그 건으로 갑니다.
// 한 건이 한 줄: 누구 · 무엇 · 확인할 것(왜 걸렸는지) · 서류 · 금액 · 판정. 숫자 카드 아래 단추로 확인 필요를 종류별로 볼 수 있습니다.
// "최근 제출"은 판정과 상관없이 가장 늦게 들어온 건입니다 — 직원이 방금 낸 건을 찾아다니지 않게 (통과한 건은 확인 필요 목록에 안 나오므로).

import ReviewStats from '../../components/ReviewStats.jsx'
import VerdictBadge from '../../components/VerdictBadge.jsx'
import StatusTag from '../../components/StatusTag.jsx'
import Icon from '../../components/Icons.jsx'
import DocsBadge from '../../components/DocsBadge.jsx'
import { STATUS } from '../../api/client.js'
import NeedsKinds from '../../components/NeedsKinds.jsx'
import { useReviewQueue, countQueue, needsCheck, problemReasons, byUrgency, byRecent, isFresh, submittedAgo, VIEW } from './reviewQueue.js'

const SHOW = 8   // 홈에 바로 보여 줄 확인 필요 건수
const RECENT = 3 // 홈에 바로 보여 줄 최근 제출 건수
const won = (n) => Number(n ?? 0).toLocaleString('ko-KR') + '원'

// 정산 한 건을 한 줄로: 누구 · 무엇 · 확인할 것 · 서류 · 금액 · 판정. (좁은 화면에서는 두 줄로 접힘)
function QueueRow({ s, acctIssue, when, plain, onOpen }) {
  const reasons = problemReasons(s, acctIssue)
  const rejected = s.status === STATUS.REJECTED
  return (
    <li>
      <button type="button" className={`queue-row${plain ? ' plain' : ''}${isFresh(s) ? ' fresh' : ''}`} onClick={() => onOpen(s.id)}>
        <span className="q-who">
          {isFresh(s) && <span className="badge new">새 제출</span>}
          <b>{s.submitter}</b> <span className="hint">{when ?? s.dept}</span>
        </span>
        <span className="q-what" title={`${s.type} · ${s.purpose}`}>{s.type} · {s.purpose}</span>
        <span className={`q-reason${reasons.length ? '' : ' none'}`} title={reasons.map((x) => x.text).join('\n')}>
          {reasons.length ? <>{reasons[0].text}{reasons.length > 1 && ` 외 ${reasons.length - 1}건`}</> : rejected ? '반려 후 다시 제출 대기' : '걸린 항목 없음'}
        </span>
        <span className="q-docs"><DocsBadge quiet docs={s.docs} /></span>
        <span className="q-amount">{won(s.amount)}</span>
        <span className="q-badge">{s.status === STATUS.PENDING ? <VerdictBadge verdict={s.verdict} /> : <StatusTag status={s.status} />}</span>
      </button>
    </li>
  )
}

export default function AdminHomePage({ user, onNavigate }) {
  const { rows, acctIssue, error } = useReviewQueue()
  const counts = rows ? countQueue(rows, acctIssue) : null
  const needs = rows ? rows.filter((r) => needsCheck(r, acctIssue)).sort(byUrgency) : []
  const recent = rows ? [...rows].sort(byRecent).slice(0, RECENT) : []

  return (
    <div className="home">
      <h1>
        {!counts ? `${user.name} 님, 안녕하세요` : counts.needs > 0 ? (
          <>{user.name} 님, 확인이 필요한 정산이 <span className="count-red">{counts.needs}건</span> 있어요</>
        ) : `${user.name} 님, 지금 확인이 필요한 정산은 없어요`}
      </h1>
      <p className="hint">AI가 먼저 점검한 결과예요. 승인·반려는 담당자가 결정해요.</p>

      {error && <div className="error" role="alert">{error}</div>}

      <ReviewStats big counts={counts} onPick={(view) => onNavigate('review', { view })} />
      {/* 확인 필요를 종류별로: 누르면 그 종류만 걸러진 검토 대기함으로 */}
      <NeedsKinds counts={counts} onPick={(kind) => onNavigate('review', { kind })} />

      {recent.length > 0 && (
        <>
          <div className="alert-head plain">
            <h2 className="home-sub">최근 제출</h2>
            <button type="button" className="link-btn" onClick={() => onNavigate('review', { view: VIEW.ALL, sort: 'recent' })}>최근 제출 순으로 모두 보기 →</button>
          </div>
          <ul className="queue-list">
            {recent.map((s) => (
              <QueueRow key={s.id} s={s} acctIssue={acctIssue} plain when={`${s.dept} · ${submittedAgo(s)}`} onOpen={(id) => onNavigate('review', { id })} />
            ))}
          </ul>
        </>
      )}

      <div className="alert-head">
        <h2 className="home-sub"><Icon name="warn" size={18} />확인 필요</h2>
        {needs.length > 0 && (
          <button type="button" className="link-btn" onClick={() => onNavigate('review', { view: VIEW.NEEDS })}>
            {needs.length > SHOW ? `${needs.length}건 모두 보기 →` : '검토 대기함에서 보기 →'}
          </button>
        )}
      </div>

      {rows === null ? (
        <div className="empty">불러오는 중…</div>
      ) : needs.length === 0 ? (
        <div className="empty">확인이 필요한 건이 없어요. 검토 대기 {counts.pending}건은 AI 점검을 통과했어요.</div>
      ) : (
        <ul className="queue-list">
          {needs.slice(0, SHOW).map((s) => (
            <QueueRow key={s.id} s={s} acctIssue={acctIssue} onOpen={(id) => onNavigate('review', { id })} />
          ))}
        </ul>
      )}

      <div className="tile-grid two">
        <button type="button" className="tile compact" onClick={() => onNavigate('review', { view: VIEW.ALL, status: STATUS.APPROVED })}>
          <span className="tile-title">승인 완료</span>
          <span className="tile-desc">승인된 정산 내역을 확인해요.</span>
          <span className="tile-go">{counts ? `${counts.approved}건` : '불러오는 중…'}</span>
        </button>
        <button type="button" className="tile compact" onClick={() => onNavigate('qa')}>
          <span className="tile-title">규정 확인하기</span>
          <span className="tile-desc">판정이 헷갈릴 때 규정 원문을 보거나 NOVA에게 물어봐요.</span>
          <span className="tile-go">확인하기 →</span>
        </button>
      </div>
    </div>
  )
}
