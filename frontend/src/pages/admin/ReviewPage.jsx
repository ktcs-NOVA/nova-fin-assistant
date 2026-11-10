// M-01 정산 검토 대기함 (목록)
// 확인이 필요한 건(보완 필요 → 담당자 확인 필요 → 확인 가능 순)이 위로 오고,
// 판정·상태로 거를 수 있습니다. 행을 누르면 상세(ReviewDetail)로 들어갑니다.
// 문제 항목에는 AI 판정 항목 외에 계정과목 불일치(M-05)도 포함해, 상세·반려 사유와 개수가 맞도록 합니다.

import { useEffect, useMemo, useState } from 'react'
import { listSubmissions, suggestAccount, VERDICT, STATUS } from '../../api/client.js'
import { compareAccount, ACCOUNT_FIELD } from '../../components/AccountReviewCard.jsx'
import VerdictBadge from '../../components/VerdictBadge.jsx'
import StatusTag from '../../components/StatusTag.jsx'
import ReviewDetail from './ReviewDetail.jsx'

const ORDER = { [VERDICT.FIX]: 0, [VERDICT.CHECK]: 1, [VERDICT.OK]: 2 }
const won = (n) => n.toLocaleString('ko-KR') + '원'

export default function ReviewPage() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [verdictFilter, setVerdictFilter] = useState('확인 필요') // '전체' | '확인 필요' | 각 판정
  const [statusFilter, setStatusFilter] = useState(STATUS.PENDING)
  const [selectedId, setSelectedId] = useState(null)
  const [acctIssue, setAcctIssue] = useState({})   // id → 계정과목 불일치·미입력 여부 (M-05, 따로 받아 채움)

  function load() {
    return listSubmissions()
      .then((data) => {
        setRows(data.items)
        setError('')
        // 계정과목 제안은 건별로 따로 받음. 실패한 건은 그냥 비워 둠 (목록은 그대로 보임)
        Promise.allSettled(data.items.map((s) => suggestAccount(s).then((d) => [s.id, !!compareAccount(s, d).issue])))
          .then((rs) => setAcctIssue(Object.fromEntries(rs.filter((r) => r.status === 'fulfilled').map((r) => r.value))))
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }
  // 외부(API)에서 데이터를 가져오는 동기화라 effect 사용. setState는 응답 후(비동기)에만 호출됨.
  useEffect(() => { load() }, [])

  // 확인 필요 = AI 판정이 확인 가능이 아니거나, 계정과목이 AI 제안과 다름
  const needsCheck = (r) => r.verdict !== VERDICT.OK || !!acctIssue[r.id]

  const counts = useMemo(() => ({
    total: rows.length,
    pending: rows.filter((r) => r.status === STATUS.PENDING).length,
    needs: rows.filter((r) => r.status === STATUS.PENDING && needsCheck(r)).length,
  }), [rows, acctIssue])

  const visible = useMemo(() => rows
    .filter((r) => statusFilter === '전체' || r.status === statusFilter)
    .filter((r) => {
      if (verdictFilter === '전체') return true
      if (verdictFilter === '확인 필요') return needsCheck(r)
      return r.verdict === verdictFilter
    })
    .sort((a, b) => ORDER[a.verdict] - ORDER[b.verdict] || a.submitted_at.localeCompare(b.submitted_at)),
  [rows, statusFilter, verdictFilter, acctIssue])

  if (selectedId) {
    return (
      <ReviewDetail
        id={selectedId}
        onBack={() => setSelectedId(null)}
        onDecided={() => { setSelectedId(null); load() }}
      />
    )
  }

  return (
    <section>
      <div className="page-title">
        <h1>정산 검토 대기함</h1>
        <span className="desc">AI가 미리 판정한 결과를 보고 승인 또는 반려합니다. 승인·반려는 사람이 누릅니다.</span>
      </div>

      {/* 요약 숫자 */}
      <div className="stat-row">
        <div className="stat"><span className="stat-label">제출</span><span className="stat-value">{counts.total}건</span></div>
        <div className="stat"><span className="stat-label">검토 대기</span><span className="stat-value">{counts.pending}건</span></div>
        <div className="stat warn"><span className="stat-label">확인 필요</span><span className="stat-value">{counts.needs}건</span></div>
      </div>

      {/* 필터 */}
      <div className="toolbar">
        <label className="field-inline">
          <span>판정</span>
          <select value={verdictFilter} onChange={(e) => setVerdictFilter(e.target.value)}>
            <option>확인 필요</option>
            <option>전체</option>
            <option>{VERDICT.FIX}</option>
            <option>{VERDICT.CHECK}</option>
            <option>{VERDICT.OK}</option>
          </select>
        </label>
        <label className="field-inline">
          <span>상태</span>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option>{STATUS.PENDING}</option>
            <option>전체</option>
            <option>{STATUS.APPROVED}</option>
            <option>{STATUS.REJECTED}</option>
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
                const problems = [...r.items.filter((it) => it.verdict !== VERDICT.OK).map((it) => it.field), ...(acctIssue[r.id] ? [ACCOUNT_FIELD] : [])]
                return (
                  <tr key={r.id} className="clickable" onClick={() => setSelectedId(r.id)}>
                    <td>{r.submitted_at.slice(5)}</td>
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
