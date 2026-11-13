// M-01 정산 검토 대기함 (목록)
// 확인이 필요한 건(검토 대기 중 보완 필요 → 담당자 확인 필요 → 계정과목 불일치, 그다음 반려한 건)이 위로 오고,
// 판정·상태로 거를 수 있습니다. 행을 누르면 상세(ReviewDetail)로 들어갑니다.
// 정렬을 "최근 제출 순"으로 바꾸면 방금 들어온 건이 맨 위에 옵니다. 1시간 안에 들어온 건은 "새 제출" 표시가 붙습니다.
// 문제 항목에는 AI 판정 항목 외에 계정과목 불일치(M-05)도 포함해, 상세·반려 사유와 개수가 맞도록 합니다.

import { useMemo, useState } from 'react'
import { VERDICT, STATUS } from '../../api/client.js'
import ReviewStats from '../../components/ReviewStats.jsx'
import VerdictBadge from '../../components/VerdictBadge.jsx'
import StatusTag from '../../components/StatusTag.jsx'
import ReviewDetail from './ReviewDetail.jsx'
import { useReviewQueue, countQueue, needsCheck, problemFields, byUrgency, byRecent, isFresh, submittedAgo, VIEW } from './reviewQueue.js'

const NEEDS = '확인 필요'
const ALL = '전체'
const won = (n) => n.toLocaleString('ko-KR') + '원'

// 정렬: 확인이 급한 순(기본) / 최근에 제출한 순 (직원이 방금 낸 건을 찾을 때)
const SORT = { URGENT: 'urgent', RECENT: 'recent' }
const SORTERS = { [SORT.URGENT]: byUrgency, [SORT.RECENT]: byRecent }

// 숫자 카드(제출 / 검토 대기 / 확인 필요) ↔ 필터 두 개. 확인 필요에는 반려 건도 들어가므로 상태는 전체로 둡니다.
const VIEW_FILTERS = {
  [VIEW.ALL]: { verdict: ALL, status: ALL },
  [VIEW.PENDING]: { verdict: ALL, status: STATUS.PENDING },
  [VIEW.NEEDS]: { verdict: NEEDS, status: ALL },
}

// param: 관리자 홈에서 넘어올 때 { view, status?, id?, sort? } — 볼 방식, 바로 열 건, 정렬
export default function ReviewPage({ param }) {
  const { rows: loaded, acctIssue, error, reload } = useReviewQueue()
  const loading = loaded === null
  const first = VIEW_FILTERS[param?.view] ?? VIEW_FILTERS[VIEW.NEEDS]
  const [verdictFilter, setVerdictFilter] = useState(first.verdict) // '전체' | '확인 필요' | 각 판정
  const [statusFilter, setStatusFilter] = useState(param?.status ?? first.status)
  const [selectedId, setSelectedId] = useState(param?.id ?? null)
  const [sort, setSort] = useState(SORTERS[param?.sort] ? param.sort : SORT.URGENT)

  const counts = useMemo(() => (loaded ? countQueue(loaded, acctIssue) : null), [loaded, acctIssue])
  const activeView = Object.keys(VIEW_FILTERS).find((v) => VIEW_FILTERS[v].verdict === verdictFilter && VIEW_FILTERS[v].status === statusFilter)

  function pickView(view) {
    setVerdictFilter(VIEW_FILTERS[view].verdict)
    setStatusFilter(VIEW_FILTERS[view].status)
  }

  const visible = useMemo(() => (loaded ?? [])
    .filter((r) => statusFilter === ALL || r.status === statusFilter)
    .filter((r) => {
      if (verdictFilter === ALL) return true
      if (verdictFilter === NEEDS) return needsCheck(r, acctIssue)
      return r.verdict === verdictFilter
    })
    .sort(SORTERS[sort]),
  [loaded, statusFilter, verdictFilter, acctIssue, sort])

  if (selectedId) {
    return (
      <ReviewDetail
        id={selectedId}
        onBack={() => setSelectedId(null)}
        onDecided={() => { setSelectedId(null); reload() }}
      />
    )
  }

  return (
    <section>
      <div className="page-title">
        <h1>정산 검토 대기함</h1>
        <span className="desc">AI가 미리 판정한 결과를 보고 승인 또는 반려합니다. 승인·반려는 사람이 누릅니다.</span>
      </div>

      {/* 요약 숫자: 누르면 그 보기로 */}
      <ReviewStats counts={counts} active={activeView} onPick={pickView} />

      {/* 필터 */}
      <div className="toolbar">
        <label className="field-inline">
          <span>판정</span>
          <select value={verdictFilter} onChange={(e) => setVerdictFilter(e.target.value)}>
            <option>{NEEDS}</option>
            <option>{ALL}</option>
            <option>{VERDICT.FIX}</option>
            <option>{VERDICT.CHECK}</option>
            <option>{VERDICT.OK}</option>
          </select>
        </label>
        <label className="field-inline">
          <span>상태</span>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option>{ALL}</option>
            <option>{STATUS.PENDING}</option>
            <option>{STATUS.APPROVED}</option>
            <option>{STATUS.REJECTED}</option>
          </select>
        </label>
        <label className="field-inline">
          <span>정렬</span>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value={SORT.URGENT}>확인이 급한 순</option>
            <option value={SORT.RECENT}>최근 제출 순</option>
          </select>
        </label>
        <span className="hint">{visible.length}건 표시</span>
      </div>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="empty">불러오는 중…</div>
      ) : visible.length === 0 ? (
        <div className="empty">조건에 맞는 제출 건이 없습니다.</div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>제출일</th><th>제출자</th><th>부서</th><th>유형</th><th>내용</th>
                <th className="num">금액</th><th>AI 판정</th><th>문제 항목</th><th>상태</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((r) => {
                const problems = problemFields(r, acctIssue)
                return (
                  <tr key={r.id} className={`clickable${isFresh(r) ? ' fresh' : ''}`} onClick={() => setSelectedId(r.id)}>
                    <td className="nowrap">{isFresh(r) ? <><span className="badge new">새 제출</span> {submittedAgo(r)}</> : r.submitted_at.slice(5)}</td>
                    <td>{r.submitter}</td>
                    <td>{r.dept}</td>
                    <td>{r.type}</td>
                    <td className="ellipsis">{r.purpose}</td>
                    <td className="num">{won(r.amount)}</td>
                    <td><VerdictBadge verdict={r.verdict} /></td>
                    <td className="ellipsis muted-text">
                      {problems.length ? problems.join(', ') : '없음'}
                    </td>
                    <td><StatusTag status={r.status} /></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
