// M-01 정산 검토 상세 — 직원 화면처럼 한 단계씩 확인하는 다섯 단계 (PM 제안, 2026-11-17)
//   1 제출 내용 → 2 AI 판정 → 3 계정과목(M-05) → 4 증빙 서류 → 5 결정(승인·반려)
// 직원 화면과 다른 점: 관리자는 건수가 많으므로
//   · 위쪽 단계를 눌러 건너뛸 수 있고, 단계마다 결과가 미리 칠해져 있음 (문제 없음 ✓ / 확인할 것 있음 !)
//   · 문제 없는 건은 첫 단계에서 바로 결정으로 갈 수 있음
//   · 결정 단계에 앞 단계 결과를 한 줄씩 요약 (판단할 때 근거가 눈앞에 있도록)
//   · 맨 위에서 이전 건·다음 건으로 이동, 결정하면 다음 건으로 넘어감 (nav — ReviewPage 가 줌)
// 결정 단계 아래: 직원에게 보이는 반려 안내 미리보기 (U-09)

import { useEffect, useState } from 'react'
import { getSubmission, decideSubmission, draftRejectMessage, suggestAccount, VERDICT, STATUS } from '../../api/client.js'
import Stepper from '../../components/Stepper.jsx'
import WizardSteps from '../../components/WizardSteps.jsx'
import VerdictBadge from '../../components/VerdictBadge.jsx'
import StatusTag from '../../components/StatusTag.jsx'
import VerifyResult from '../../components/VerifyResult.jsx'
import AttachedDocs from '../../components/AttachedDocs.jsx'
import DocsBadge from '../../components/DocsBadge.jsx'
import AccountReviewCard, { compareAccount, ACCOUNT_FIELD } from '../../components/AccountReviewCard.jsx'

const won = (n) => n.toLocaleString('ko-KR') + '원'
const STEPS = ['제출 내용', 'AI 판정', '계정과목', '증빙 서류', '결정']
const DOC_NAME = { 지출결과서: '지출 결과서' }

// nav: 목록에서의 위치와 앞뒤 건 { index, total, prevId, nextId, onGo(id) } — 없으면(목록 밖의 건) 이동 버튼을 숨김
export default function ReviewDetail({ id, onBack, onDecided, nav }) {
  const [sub, setSub] = useState(null)
  const [step, setStep] = useState(1)             // 1~5 (STEPS)
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
  // 회의비 건이면 첫 항목에 회의 목적·참석자가 실려 옴 (직원 청구 검증 화면에서 필수 입력)
  const meetingInfo = sub.type === '회의비' ? (sub.expenses?.[0] ?? {}) : null

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
      // 반려면 고른 사유 항목을 함께 저장 → 직원의 "내 정산 현황"에 항목별(문제·근거·수정 방법)로 보임
      const issues = decision === STATUS.REJECTED
        ? problems.filter((it) => picked.includes(it.field)).map(({ field, verdict, message, basis, fix }) => ({ field, verdict, message, basis, fix }))
        : undefined
      await decideSubmission(sub.id, decision, draft, issues)
      onDecided()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const go = (n) => { setError(''); setStep(n); window.scrollTo?.(0, 0) }

  // 단계별 결과: 위쪽 단계 표시와 결정 단계 요약이 같이 씀
  const aiIssues = sub.items.filter((it) => it.verdict !== VERDICT.OK)
  const fixCount = aiIssues.filter((it) => it.verdict === VERDICT.FIX).length
  const checkCount = aiIssues.length - fixCount
  const docsMissing = sub.docs?.missing ?? []
  const marks = [
    'ok',
    aiIssues.length ? 'issue' : 'ok',
    acct.loading || acct.error ? undefined : accountIssue ? 'issue' : 'ok',
    sub.docs ? (docsMissing.length ? 'issue' : 'ok') : undefined,
    decided ? 'ok' : undefined,
  ]
  const clean = marks.slice(0, 4).every((m) => m === 'ok')   // 앞 네 단계에 확인할 것이 없는 건
  const counts = [fixCount && `보완 필요 ${fixCount}건`, checkCount && `담당자 확인 ${checkCount}건`].filter(Boolean).join(' · ')
  const summary = [
    { step: 2, label: 'AI 판정', ok: !aiIssues.length,
      text: aiIssues.length ? `${counts} — ${aiIssues[0].field}: ${aiIssues[0].message}` : '확인한 규정 기준을 모두 충족' },
    { step: 3, label: '계정과목', ok: marks[2] === 'ok', pending: marks[2] === undefined,
      text: acct.loading ? 'AI 제안을 받는 중…' : acct.error ? 'AI 제안을 받지 못했어요' : accountIssue ? accountIssue.message : `직원 입력(${sub.account})과 AI 제안이 같음` },
    { step: 4, label: '증빙 서류', ok: marks[3] === 'ok', pending: marks[3] === undefined,
      text: !sub.docs ? '서류 상태를 알 수 없어요'
        : docsMissing.length ? `아직 안 온 서류: ${docsMissing.map((k) => DOC_NAME[k] ?? k).join(', ')}`
        : `${sub.docs.expected.length}종 모두 받음` },
  ]

  const stepNav = (
    <div className="wiz-nav">
      {step > 1 ? <button type="button" className="btn" onClick={() => go(step - 1)}>이전</button> : <span />}
      <span className="btn-row">
        {step === 1 && clean && !decided && <button type="button" className="btn" onClick={() => go(5)}>문제 없는 건 · 바로 결정으로</button>}
        <button type="button" className="btn primary" onClick={() => go(step + 1)}>확인했어요, 다음</button>
      </span>
    </div>
  )

  return (
    <section className="wizard review-wizard">
      <div className="toolbar">
        <button type="button" className="btn" onClick={onBack}>← 목록</button>
        <span className="hint">{sub.id}{nav ? ` · ${nav.total}건 중 ${nav.index + 1}번째` : ''}</span>
        {nav && (
          <span className="review-nav">
            <button type="button" className="btn small" disabled={!nav.prevId} onClick={() => nav.onGo(nav.prevId)}>← 이전 건</button>
            <button type="button" className="btn small" disabled={!nav.nextId} onClick={() => nav.onGo(nav.nextId)}>다음 건 →</button>
          </span>
        )}
      </div>

      {/* 어느 단계에서도 지금 보는 건이 무엇인지 보이도록 */}
      <div className="card review-head">
        <div>
          <h1>{sub.purpose}</h1>
          <span className="hint">{sub.submitter} · {sub.dept} · {sub.type} · {won(sub.amount)}</span>
        </div>
        <div className="info-badges"><VerdictBadge verdict={sub.verdict} /><DocsBadge docs={sub.docs} /><StatusTag status={sub.status} /></div>
      </div>

      <WizardSteps steps={STEPS} current={step} marks={marks} onPick={go} />

      {/* ---------- 1. 제출 내용 ---------- */}
      {step === 1 && (
        <div className="wiz-step">
          <div className="wiz-step-head">
            <h2>1. 누가 무엇을 냈는지 확인해 주세요</h2>
            <p className="hint">직원이 제출한 내용 그대로예요. 위 단계에 ! 가 붙은 곳이 확인할 것이 있는 단계입니다.</p>
          </div>
          <div className="card info-card">
            <dl className="info-grid">
              <dt>제출자</dt><dd>{sub.submitter} · {sub.dept}</dd>
              <dt>유형</dt><dd>{sub.type}</dd>
              <dt>사용일시</dt><dd>{sub.date}{sub.time ? ` ${sub.time}` : ''}</dd>
              {sub.merchant && (<><dt>사용처</dt><dd>{sub.merchant}</dd></>)}
              {/* 회의비: 실무에서 증빙으로 보는 두 가지 (회의 목적·참석자) */}
              {meetingInfo?.meeting_purpose && (<><dt>회의 목적</dt><dd>{meetingInfo.meeting_purpose}</dd></>)}
              {meetingInfo && (<><dt>참석자</dt><dd>{meetingInfo.attendees?.length ? `${meetingInfo.attendees.join(', ')}${meetingInfo.participant_count ? ` · 총 ${meetingInfo.participant_count}명` : ''}` : <span className="error-text">미기재</span>}</dd></>)}
              <dt>금액</dt><dd>{won(sub.amount)}</dd>
              <dt>계정과목</dt><dd>{sub.account || <span className="muted-text">미입력</span>}</dd>
              <dt>제출일</dt><dd>{sub.submitted_at}</dd>
              {sub.resubmit_of && (<><dt>다시 제출</dt><dd>반려한 <b>{sub.resubmit_of}</b> 건을 직원이 고쳐서 다시 낸 정산</dd></>)}
            </dl>
          </div>
          <details className="wiz-more">
            <summary>이 정산의 처리 단계 보기</summary>
            <Stepper current={sub.step} status={sub.status} />
          </details>
          {stepNav}
        </div>
      )}

      {/* ---------- 2. AI 판정 (직원 화면과 같은 결과 카드) ---------- */}
      {step === 2 && (
        <div className="wiz-step">
          <div className="wiz-step-head">
            <h2>2. AI가 미리 점검한 결과예요</h2>
            <p className="hint">{aiIssues.length ? `규정 기준에 걸린 항목이 ${aiIssues.length}건 있어요. 근거 조항과 함께 확인해 주세요.` : '규정 기준에 걸린 항목이 없어요.'}</p>
          </div>
          <VerifyResult result={{ overall: sub.verdict, items: sub.items }} />
          {stepNav}
        </div>
      )}

      {/* ---------- 3. 계정과목 (M-05) ---------- */}
      {step === 3 && (
        <div className="wiz-step">
          <div className="wiz-step-head">
            <h2>3. 계정과목이 맞는지 봐 주세요</h2>
            <p className="hint">직원이 적은 과목과 AI가 제안한 과목을 나란히 비교했어요.</p>
          </div>
          <AccountReviewCard submission={sub} suggestion={acct.data} loading={acct.loading} error={acct.error} />
          {stepNav}
        </div>
      )}

      {/* ---------- 4. 증빙 서류 ---------- */}
      {step === 4 && (
        <div className="wiz-step">
          <div className="wiz-step-head">
            <h2>4. 직원이 보낸 서류를 확인해 주세요</h2>
            <p className="hint">지출 결과서·검수확인서, 회의록, 출장보고서가 양식 그대로 보여요. 영수증 사진도 여기에 있어요.</p>
          </div>
          <AttachedDocs code={sub.id} />
          {stepNav}
        </div>
      )}

      {/* ---------- 5. 결정 ---------- */}
      {step === 5 && (
        <div className="wiz-step">
          <div className="wiz-step-head">
            <h2>5. {decided ? '처리한 결과예요' : '승인할지 반려할지 정해 주세요'}</h2>
            <p className="hint">앞 단계에서 본 내용을 한 줄씩 모았어요. 줄을 누르면 그 단계로 돌아가요. 승인·반려는 담당자가 결정해요.</p>
          </div>
          <ul className="review-summary">
            {summary.map((r) => (
              <li key={r.label}>
                <button type="button" className={r.pending ? 'pending' : r.ok ? 'ok' : 'issue'} onClick={() => go(r.step)}>
                  <b>{r.label}</b>
                  <span>{r.text}</span>
                </button>
              </li>
            ))}
          </ul>
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
                  rows={6}
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
                <p className="hint">직원의 “내 정산 현황”에는 체크한 사유가 항목별로(문제 · 근거 · 고치는 방법) 보이고, 이 메시지는 원문으로 함께 보입니다.</p>
              </div>
            </>
          )}
          <div className="wiz-nav">
            <button type="button" className="btn" onClick={() => go(4)}>이전</button>
            {decided && nav?.nextId && <button type="button" className="btn primary" onClick={() => nav.onGo(nav.nextId)}>다음 건 →</button>}
          </div>
        </div>
      )}
    </section>
  )
}
