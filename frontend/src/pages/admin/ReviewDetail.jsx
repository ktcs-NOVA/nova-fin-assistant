// M-01 정산 검토 상세
// 상단: 처리 단계(Stepper) + 제출 정보
// 가운데: AI 판정 결과 (직원 U-04와 같은 결과 카드 재사용) + 계정과목 검토 (M-05)
// 아래: 반려 패널 (사유 선택 → 메시지 초안 생성 → 수정 → 반려) / 승인 버튼
// 맨 아래: 직원에게 보이는 반려 안내 미리보기 (U-09)

import { useEffect, useState } from 'react'
import { getSubmission, decideSubmission, draftRejectMessage, suggestAccount, VERDICT, STATUS } from '../../api/client.js'
import Stepper from '../../components/Stepper.jsx'
import VerdictBadge from '../../components/VerdictBadge.jsx'
import StatusTag from '../../components/StatusTag.jsx'
import VerifyResult from '../../components/VerifyResult.jsx'
import AccountReviewCard, { compareAccount, ACCOUNT_FIELD } from '../../components/AccountReviewCard.jsx'

const won = (n) => n.toLocaleString('ko-KR') + '원'

export default function ReviewDetail({ id, onBack, onDecided }) {
  const [sub, setSub] = useState(null)
  const [error, setError] = useState('')
  const [picked, setPicked] = useState([])        // 반려 사유로 고른 항목 field 목록
  const [draft, setDraft] = useState('')           // 반려 메시지 (초안 생성 후 수정 가능)
  const [drafting, setDrafting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [acct, setAcct] = useState({ loading: true, data: null, error: '' })  // M-05 AI 계정과목 제안

  useEffect(() => {
    setAcct({ loading: true, data: null, error: '' })
    getSubmission(id).then((s) => {
      setSub(s)
      // 문제 항목은 기본으로 체크해 둠
      setPicked(s.items.filter((it) => it.verdict !== VERDICT.OK).map((it) => it.field))
      // 계정과목 제안은 따로 받음 (실패해도 상세는 그대로 보임)
      suggestAccount(s).then((data) => {
        setAcct({ loading: false, data, error: '' })
        // 불일치·미입력이면 반려 사유 후보에 기본으로 체크
        if (compareAccount(s, data).issue) setPicked((p) => (p.includes(ACCOUNT_FIELD) ? p : [...p, ACCOUNT_FIELD]))
      }).catch((e) => setAcct({ loading: false, data: null, error: e.message }))
    }).catch((e) => setError(e.message))
  }, [id])

  if (error && !sub) return <div className="error">{error}</div>
  if (!sub) return <div className="empty">불러오는 중…</div>

  // 반려 사유 후보 = AI 판정 문제 항목 + 계정과목 불일치(M-05)
  const accountIssue = acct.data ? compareAccount(sub, acct.data).issue : null
  const problems = [...sub.items.filter((it) => it.verdict !== VERDICT.OK), ...(accountIssue ? [accountIssue] : [])]
  const decided = sub.status !== STATUS.PENDING

  function toggle(field) {
    setPicked((p) => (p.includes(field) ? p.filter((f) => f !== field) : [...p, field]))
  }

  async function makeDraft() {
    setDrafting(true)
    setError('')
    try {
      const extra = accountIssue && picked.includes(ACCOUNT_FIELD) ? [accountIssue] : []
      const r = await draftRejectMessage(sub.id, picked.filter((f) => f !== ACCOUNT_FIELD), extra)
      setDraft(r.message)
    } catch (e) {
      setError(e.message)
    } finally {
      setDrafting(false)
    }
  }

  async function decide(decision) {
    if (decision === STATUS.REJECTED && !draft.trim()) {
      setError('반려 메시지를 먼저 작성해 주세요.')
      return
    }
    if (!window.confirm(`이 건을 "${decision}" 처리할까요?`)) return
    setSaving(true)
    setError('')
    try {
      await decideSubmission(sub.id, decision, draft)
      onDecided()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section>
      <div className="toolbar">
        <button className="btn" onClick={onBack}>← 목록</button>
        <span className="hint">{sub.id}</span>
      </div>

      <Stepper current={sub.step} />

      {/* 제출 정보 */}
      <div className="card info-card">
        <div className="info-head">
          <h2>{sub.purpose}</h2>
          <div className="info-badges"><VerdictBadge verdict={sub.verdict} /><StatusTag status={sub.status} /></div>
        </div>
        <dl className="info-grid">
          <dt>제출자</dt><dd>{sub.submitter} · {sub.dept}</dd>
          <dt>유형</dt><dd>{sub.type}</dd>
          <dt>사용일시</dt><dd>{sub.date}{sub.time ? ` ${sub.time}` : ''}</dd>
          {sub.merchant && (<><dt>사용처</dt><dd>{sub.merchant}</dd></>)}
          <dt>금액</dt><dd>{won(sub.amount)}</dd>
          <dt>계정과목</dt><dd>{sub.account || <span className="muted-text">미입력</span>}</dd>
          <dt>제출일</dt><dd>{sub.submitted_at}</dd>
        </dl>
      </div>

      {/* AI 판정 결과: 직원 화면과 같은 카드 */}
      <h2 className="section-title">AI 사전검증 결과</h2>
      <VerifyResult result={{ overall: sub.verdict, items: sub.items }} />

      {/* M-05: 직원이 적은 계정과목 vs AI 제안 */}
      <h2 className="section-title">계정과목 검토</h2>
      <AccountReviewCard submission={sub} suggestion={acct.data} loading={acct.loading} error={acct.error} />

      {/* 검토 패널 */}
      <h2 className="section-title">검토</h2>
      {error && <div className="error">{error}</div>}
      {decided ? (
        <div className="card">
          <p><StatusTag status={sub.status} /> 처리 완료 ({sub.decided_at ?? '-'})</p>
          {sub.decision_message && <pre className="message-box">{sub.decision_message}</pre>}
        </div>
      ) : (
        <div className="card review-panel">
          <div className="review-col">
            <h3>반려 사유 선택</h3>
            {problems.length === 0 && <p className="hint">AI가 찾은 문제 항목이 없습니다. 반려하려면 직접 메시지를 작성하세요.</p>}
            <ul className="check-list">
              {problems.map((it) => (
                <li key={it.field}>
                  <label>
                    <input type="checkbox" checked={picked.includes(it.field)} onChange={() => toggle(it.field)} />
                    <span><b>{it.field}</b> · {it.message} <span className="muted-text">({it.basis})</span></span>
                  </label>
                </li>
              ))}
            </ul>
            <button className="btn" onClick={makeDraft} disabled={drafting || picked.length === 0}>
              {drafting ? '작성 중…' : '근거 기반 반려 메시지 초안 생성'}
            </button>
            <p className="hint">초안은 백엔드가 규정 근거(RAG)로 작성합니다. 내용을 확인하고 고친 뒤 반려하세요.</p>
          </div>

          <div className="review-col">
            <h3>반려 메시지</h3>
            <textarea
              rows={10}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="초안을 생성하거나 직접 작성하세요."
            />
            <div className="btn-row">
              <button className="btn danger" onClick={() => decide(STATUS.REJECTED)} disabled={saving}>반려</button>
              <button className="btn primary" onClick={() => decide(STATUS.APPROVED)} disabled={saving}>승인</button>
            </div>
          </div>
        </div>
      )}

      {/* U-09 미리보기: 반려하면 직원에게 이렇게 보임 */}
      {!decided && draft && (
        <>
          <h2 className="section-title">직원에게 보이는 안내 (미리보기)</h2>
          <div className="card preview-card">
            <div className="preview-head"><StatusTag status={STATUS.REJECTED} /> <b>{sub.purpose}</b> 정산이 반려되었습니다</div>
            <pre className="message-box">{draft}</pre>
            <p className="hint">직원 화면에서는 각 근거 조항을 누르면 규정 원문과 수정 방법 안내(U-09)가 열립니다.</p>
          </div>
        </>
      )}
    </section>
  )
}
