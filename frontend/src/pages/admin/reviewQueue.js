// 관리자 홈과 검토 대기함이 같이 쓰는 "제출 목록 + 건수" 로직.
// 두 화면의 숫자가 어긋나지 않도록 "확인 필요" 기준을 여기 한 곳에만 둡니다 (2026-11-13 코칭 반영).
//
//   제출      전체 제출 건
//   검토 대기 아직 승인·반려하지 않은 건
//   확인 필요 검토 대기 중 AI 판정이 "규정상 확인 가능"이 아니거나 계정과목이 AI 제안과 다른 건 + 반려한 건
//             (반려는 따로 세지 않고 확인 필요에 포함)

import { useCallback, useEffect, useState } from 'react'
import { listSubmissions, suggestAccount, STATUS, VERDICT } from '../../api/client.js'
import { compareAccount, ACCOUNT_FIELD } from '../../components/AccountReviewCard.jsx'

// 홈의 숫자 카드를 눌러 검토 대기함으로 갈 때 넘기는 보기 방식
export const VIEW = { ALL: 'all', PENDING: 'pending', NEEDS: 'needs' }

// 계정과목 제안(M-05)은 건별로 따로 받아야 해서, 화면을 오갈 때 다시 부르지 않게 기억해 둡니다.
const acctCache = new Map()
function accountIssue(s) {
  const key = `${s.id}|${s.account ?? ''}|${s.amount}`
  if (!acctCache.has(key)) {
    const p = suggestAccount(s).then((d) => !!compareAccount(s, d).issue)
    p.catch(() => acctCache.delete(key))   // 실패한 건은 다음에 다시 시도
    acctCache.set(key, p)
  }
  return acctCache.get(key)
}

/** 제출 목록과 계정과목 불일치 여부. rows 가 null 이면 아직 불러오는 중. */
export function useReviewQueue() {
  const [rows, setRows] = useState(null)
  const [acctIssue, setAcctIssue] = useState({})   // id → 계정과목 불일치·미입력 여부
  const [error, setError] = useState('')

  const reload = useCallback(() => listSubmissions()
    .then((data) => {
      const items = data.items ?? []
      setRows(items)
      setError('')
      // 실패한 건은 비워 둠 (목록은 그대로 보임)
      Promise.allSettled(items.map((s) => accountIssue(s).then((bad) => [s.id, bad])))
        .then((rs) => setAcctIssue(Object.fromEntries(rs.filter((r) => r.status === 'fulfilled').map((r) => r.value))))
    })
    .catch((e) => { setRows([]); setError(e.message) }), [])

  // 외부(API)에서 데이터를 가져오는 동기화라 effect 사용. setState 는 응답 후(비동기)에만 호출됨.
  useEffect(() => { reload() }, [reload])

  return { rows, acctIssue, error, reload }
}

/** 이 건이 "확인 필요"인지 */
export function needsCheck(r, acctIssue) {
  if (r.status === STATUS.REJECTED) return true
  return r.status === STATUS.PENDING && (r.verdict !== VERDICT.OK || !!acctIssue[r.id])
}

/** 숫자 카드 3종 + 확인 필요의 내역 */
export function countQueue(rows, acctIssue) {
  const pending = rows.filter((r) => r.status === STATUS.PENDING)
  return {
    total: rows.length,
    pending: pending.length,
    needs: rows.filter((r) => needsCheck(r, acctIssue)).length,
    fix: pending.filter((r) => r.verdict === VERDICT.FIX).length,
    check: pending.filter((r) => r.verdict === VERDICT.CHECK).length,
    account: pending.filter((r) => r.verdict === VERDICT.OK && acctIssue[r.id]).length,   // AI 판정은 통과했지만 계정과목이 다른 건
    rejected: rows.filter((r) => r.status === STATUS.REJECTED).length,
    approved: rows.filter((r) => r.status === STATUS.APPROVED).length,
  }
}

/** 문제 항목 이름들 (AI 판정에서 걸린 항목 + 계정과목) */
export function problemFields(r, acctIssue) {
  return [
    ...(r.items ?? []).filter((it) => it.verdict !== VERDICT.OK).map((it) => it.field),
    ...(acctIssue[r.id] ? [ACCOUNT_FIELD] : []),
  ]
}

const VERDICT_ORDER = { [VERDICT.FIX]: 0, [VERDICT.CHECK]: 1, [VERDICT.OK]: 2 }
const STATUS_ORDER = { [STATUS.PENDING]: 0, [STATUS.REJECTED]: 1, [STATUS.APPROVED]: 2 }

/** 검토 대기 → 반려 → 승인, 그 안에서 보완 필요 → 담당자 확인 → 확인 가능, 먼저 제출한 순 */
export function byUrgency(a, b) {
  return (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9)
    || (VERDICT_ORDER[a.verdict] ?? 9) - (VERDICT_ORDER[b.verdict] ?? 9)
    || String(a.submitted_at ?? '').localeCompare(String(b.submitted_at ?? ''))
}

// ---- 최근 제출 (직원이 방금 낸 건을 관리자가 바로 찾을 수 있게) ----
// submitted_time 은 분 단위 제출 시각(예: 2026-11-13T15:02+09:00). 목업처럼 없으면 제출일(submitted_at)로 대신합니다.

const FRESH_MINUTES = 60   // 이 안에 들어온 건은 "새 제출"로 표시
const codeNo = (r) => Number(String(r.id ?? '').split('-').pop()) || 0
const submittedMs = (r) => Date.parse(r.submitted_time ?? r.submitted_at ?? '') || 0

/** 최근에 제출한 순. 시각이 같으면 제출 번호가 큰 쪽이 먼저 */
export function byRecent(a, b) {
  return submittedMs(b) - submittedMs(a) || codeNo(b) - codeNo(a)
}

/** 방금 들어온 건인지 (제출 시각이 있을 때만) */
export function isFresh(r, now = Date.now()) {
  if (!r.submitted_time) return false
  const min = (now - submittedMs(r)) / 60000
  return min >= 0 && min < FRESH_MINUTES
}

/** "방금 전" / "12분 전" / "3시간 전" / "11-12" */
export function submittedAgo(r, now = Date.now()) {
  if (!r.submitted_time) return (r.submitted_at ?? '').slice(5)
  const min = Math.floor((now - submittedMs(r)) / 60000)
  if (min < 1) return '방금 전'
  if (min < 60) return `${min}분 전`
  if (min < 24 * 60) return `${Math.floor(min / 60)}시간 전`
  return r.submitted_time.slice(5, 10)
}
