// 내 정산 현황의 반려 건 카드 (U-09 반려 사유 해석·수정 안내).
// 관리자가 고른 반려 사유를 항목별로 — 무엇이 문제인지, 근거 조항, 어떻게 고치는지 — 보여 주고
// 바로 고쳐서 다시 제출할 수 있게 합니다. 근거 조항을 누르면 규정 물어보기에서 그 조항을 찾아 줍니다.
// 이미 고쳐서 다시 낸 건은 접힌 채로 새 제출 번호만 알려 줍니다.

import { useState } from 'react'
import { VERDICT } from '../api/client.js'
import { resubmitPrefill } from '../utils/resubmit.js'

const won = (n) => Number(n ?? 0).toLocaleString('ko-KR') + '원'
const day = (iso) => {
  const [, m, d] = String(iso ?? '').split('-').map(Number)
  return m ? `${m}월 ${d}일` : ''
}

export default function RejectedCard({ sub, user, onNavigate, onSendToVerify }) {
  const issues = sub.decision_issues ?? []
  const again = sub.resubmitted_as
  const [open, setOpen] = useState(!again)          // 다시 낸 건은 접어 둠
  const [showMessage, setShowMessage] = useState(issues.length === 0)   // 항목이 없으면 담당자 메시지를 바로 보여 줌

  const ask = (text) => onNavigate?.('qa', { ask: text })
  const askAll = () => ask(`정산이 반려됐어. 사유는 "${issues.slice(0, 2).map((i) => i.message).join(' / ') || sub.decision_message?.slice(0, 120)}" 인데, 어떻게 고쳐서 다시 내면 돼?`)

  return (
    <li className={`rejected-card${again ? ' settled' : ''}`}>
      <div className="rejected-head">
        <div>
          <div className="recent-name">{sub.type} · {sub.purpose}</div>
          <div className="hint">{sub.date} · {won(sub.amount)} · {sub.id}</div>
        </div>
        <span className="badge bad">반려{sub.decided_at ? ` · ${day(sub.decided_at)}` : ''}</span>
      </div>

      {again && (
        <div className="rejected-again">
          <span><b>{again}</b> 번으로 고쳐서 다시 제출했어요.</span>
          <button type="button" className="link-btn" onClick={() => setOpen(!open)}>{open ? '사유 접기' : '반려 사유 보기'}</button>
        </div>
      )}

      {open && (
        <div className="rejected-body">
          {issues.length > 0 && <div className="hint">반려 사유 {issues.length}건 · 사유마다 고치는 방법을 함께 적었어요.</div>}
          <ol className="rejected-issues">
            {issues.map((it, i) => (
              <li key={i} className={it.verdict === VERDICT.FIX ? 'fix' : 'check'}>
                <b>{i + 1}. {it.field}</b>
                {it.message && <p>{it.message}</p>}
                {it.basis && (
                  <button type="button" className="link-btn rejected-basis" onClick={() => ask(`${it.basis} 내용을 알려줘`)}>
                    근거 · {it.basis} ›
                  </button>
                )}
                {it.fix && <div className="rejected-fix">이렇게 고치세요 · {it.fix}</div>}
              </li>
            ))}
          </ol>

          {showMessage && sub.decision_message && (
            <div>
              <div className="hint">회계 담당자가 남긴 메시지</div>
              <pre className="message-box">{sub.decision_message}</pre>
            </div>
          )}

          <div className="btn-row rejected-actions">
            <button type="button" className="btn small" onClick={askAll}>규정 물어보기</button>
            {issues.length > 0 && sub.decision_message && (
              <button type="button" className="btn small" onClick={() => setShowMessage(!showMessage)}>{showMessage ? '메시지 접기' : '담당자 메시지 원문'}</button>
            )}
            {!again && (
              <button type="button" className="btn small primary" onClick={() => onSendToVerify?.(resubmitPrefill(sub, user))}>고쳐서 다시 제출</button>
            )}
          </div>
        </div>
      )}
    </li>
  )
}
