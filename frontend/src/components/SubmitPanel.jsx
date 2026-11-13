// 청구 검증(U-04) 결과 아래 "검토 요청(제출)" 패널
// 검증을 마친 청구 내역을 관리자 검토 대기함(M-01)으로 보냅니다. 건명과 계정과목(M-05 비교용)을 함께 적습니다.

import { useEffect, useState } from 'react'
import { createSubmission, ACCOUNTS, VERDICT } from '../api/client.js'
import NextDocs from './NextDocs.jsx'
import { docsForClaim } from '../utils/claimToDocs.js'

const DEFAULT_ACCOUNT = { 국내출장: '여비교통비', 업무추진비: '업무추진비', 법인카드: '' }
// 회의비: 외부 참석(업무추진비 기준으로 검사한 건)이면 업무추진비, 내부 회의면 조직관리비
function defaultAccount(claim) {
  if (claim.trip_type === '회의비') return claim.items?.[0]?.category === 'business' ? '업무추진비' : '조직관리비'
  return DEFAULT_ACCOUNT[claim.trip_type] ?? ''
}

function defaultPurpose(claim) {
  // trip.region 은 "서울/광역시/기타" 같은 지역 구분이라 이름처럼 붙이지 않고 괄호로 보임
  if (claim.trip?.start_date) return `출장 여비 정산 (${claim.trip.start_date}${claim.trip.end_date ? `~${claim.trip.end_date}` : ''}${claim.trip.region ? `, ${claim.trip.region}` : ''})`
  if (claim.trip?.region) return `출장 여비 정산 (${claim.trip.region})`
  if (claim.items?.[0]?.meeting_purpose) return claim.items[0].meeting_purpose   // 회의비는 회의 목적이 곧 건명
  const first = claim.items?.[0]?.field
  return first ? `${first} (${claim.trip_type})` : `${claim.trip_type} 지출 정산`
}

export default function SubmitPanel({ claim, result, user, onNavigate }) {
  const [purpose, setPurpose] = useState(() => defaultPurpose(claim))
  const [account, setAccount] = useState(() => defaultAccount(claim))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(null)   // 제출 완료된 건

  // 새로 검증하면 제출 상태 초기화
  useEffect(() => { setDone(null); setError('') }, [result])

  const fixCount = result.items.filter((it) => it.verdict === VERDICT.FIX).length

  async function submit() {
    if (!purpose.trim()) { setError('건명을 적어 주세요.'); return }
    if (fixCount && !window.confirm(`'보완 필요' ${fixCount}건이 남아 있습니다. 그대로 제출하면 반려될 수 있습니다. 제출할까요?`)) return
    setBusy(true)
    setError('')
    try {
      setDone(await createSubmission(claim, { purpose: purpose.trim(), account: account || null, verify_result: result }))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <div className="card submit-panel submit-done">
        <b>{done.id}</b> 번으로 제출되었습니다. 회계 관리자 검토를 기다리는 중입니다.
        <div className="hint">건명 {done.purpose} · 합계 {done.amount.toLocaleString('ko-KR')}원{done.account ? ` · 계정과목 ${done.account}` : ''}</div>
        {/* 정산 → 문서 작성: 입력한 값으로 채운 서류 화면으로 (제출 번호를 함께 넘김) */}
        <NextDocs src={{ ...claim, id: done.id, amount: done.amount }} user={user} onNavigate={onNavigate} />
      </div>
    )
  }

  return (
    <div className="card submit-panel">
      <h3>검토 요청 (제출)</h3>
      <p className="hint">판정 결과와 함께 회계 관리자 검토 대기함으로 보냅니다. 계정과목은 관리자 화면에서 AI 제안과 비교됩니다.</p>
      <div className="submit-fields">
        <label className="field">
          <span className="field-label">건명</span>
          <input type="text" value={purpose} onChange={(e) => setPurpose(e.target.value)} placeholder="예: 부산 선사 방문 출장 여비" />
        </label>
        <label className="field">
          <span className="field-label">계정과목 <em>결의서에 적을 과목</em></span>
          <select value={account} onChange={(e) => setAccount(e.target.value)}>
            <option value="">선택 안 함</option>
            {ACCOUNTS.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </label>
      </div>
      {error && <div className="error">{error}</div>}
      {docsForClaim(claim, user).length > 0 && (
        <p className="hint">제출하면 입력한 내용으로 {docsForClaim(claim, user).map((d) => d.kind).join('·')} 초안을 이어서 쓸 수 있어요.</p>
      )}
      <div className="btn-row between">
        <span className="hint">{fixCount ? `보완 필요 ${fixCount}건 — 고친 뒤 제출을 권장` : '보완 필요 항목 없음'}</span>
        <button type="button" className="btn primary" onClick={submit} disabled={busy}>{busy ? '제출 중…' : '검토 요청(제출)'}</button>
      </div>
    </div>
  )
}
