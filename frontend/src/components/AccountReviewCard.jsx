// M-05 계정과목 검토 카드: 직원이 적은 계정과목과 AI 제안(U-07 suggest_account)을 나란히 비교
// 불일치면 경고를 띄우고, ReviewDetail 이 반려 사유 후보("계정과목")를 하나 추가합니다.

import { VERDICT } from '../api/client.js'

export const ACCOUNT_FIELD = '계정과목'
const UNRESOLVED = '담당자 확인'

/**
 * 비교 결과. state:
 *   pending     아직 AI 제안을 못 받음
 *   match       직원 입력 = AI 제안
 *   mismatch    둘이 다름 → issue(반려 사유 후보) 포함
 *   unresolved  AI가 과목을 정하지 못함 (담당자 확인)
 *   missing     직원이 계정과목을 안 적음 → issue 포함
 */
export function compareAccount(sub, suggestion) {
  if (!suggestion) return { state: 'pending' }
  const mine = (sub.account ?? '').trim()
  const ai = suggestion.account

  if (!mine) {
    return {
      state: 'missing',
      issue: {
        field: ACCOUNT_FIELD,
        verdict: VERDICT.FIX,
        message: ai === UNRESOLVED ? '계정과목이 비어 있고, AI도 항목명만으로는 과목을 정하지 못했습니다.' : `계정과목이 비어 있습니다. AI 제안: "${ai}"`,
        basis: suggestion.basis || '회계규정 시행세칙 제7조 제1호 (결의서 기재 사항)',
        fix: ai === UNRESOLVED ? '계정과목을 적고 담당자와 확인' : `계정과목 "${ai}" 기재`,
      },
    }
  }
  if (ai === UNRESOLVED) return { state: 'unresolved' }
  if (mine === ai) return { state: 'match' }
  return {
    state: 'mismatch',
    issue: {
      field: ACCOUNT_FIELD,
      verdict: VERDICT.CHECK,
      message: `직원 입력 "${mine}", AI 제안 "${ai}" 로 서로 다릅니다.`,
      basis: suggestion.basis,
      fix: `AI 제안 "${ai}" 로 수정하거나, "${mine}" 유지 사유를 적어 제출`,
    },
  }
}

const STATE_LABEL = {
  pending: '확인 중…',
  match: '일치',
  mismatch: '불일치 · 확인 필요',
  unresolved: 'AI 미확정 · 담당자 확인',
  missing: '직원 입력 없음',
}

export default function AccountReviewCard({ submission, suggestion, loading, error }) {
  const cmp = compareAccount(submission, suggestion)
  const state = loading ? 'pending' : cmp.state

  return (
    <div className={`card account-card state-${state}`}>
      <div className="account-head">
        <span className={`account-state ${state}`}>{STATE_LABEL[state]}</span>
        <span className="hint">AI 제안은 결의서 초안 작성 규칙을 기준으로 합니다.</span>
      </div>

      <div className="account-compare">
        <div className="account-col">
          <span className="label">직원 입력</span>
          <div className="account-name">{submission.account || <span className="muted-text">(없음)</span>}</div>
          <div className="account-sub">결의서에 직원이 적은 과목</div>
        </div>
        <div className="account-arrow" aria-hidden="true">↔</div>
        <div className="account-col">
          <span className="label">AI 제안</span>
          {error ? (
            <div className="account-name error-text">받지 못함</div>
          ) : loading || !suggestion ? (
            <div className="account-name muted-text">확인 중…</div>
          ) : (
            <>
              <div className="account-name">
                {suggestion.account}
                <span className={`badge ${suggestion.confidence === '규정 확인' ? 'good' : 'warn'}`}>{suggestion.confidence}</span>
              </div>
              <div className="account-sub">{suggestion.sub_accounts.length ? suggestion.sub_accounts.join(' · ') : '세목 없음'}</div>
            </>
          )}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {suggestion?.basis && !error && <p className="account-basis"><b>근거</b> {suggestion.basis}</p>}

      {cmp.issue && !loading && (
        <p className="account-note">
          반려 사유 후보에 <b>{ACCOUNT_FIELD}</b> 항목을 추가했습니다. {cmp.issue.fix}
        </p>
      )}
      {state === 'unresolved' && (
        <p className="account-note">AI가 과목을 정하지 못한 건입니다. 직원 입력이 맞는지 회계책임자가 확인하세요 (회계규정 시행세칙 제6조 제3항).</p>
      )}
    </div>
  )
}
