// "지출내역 엑셀" 내려받기 버튼. 직원 화면에서는 내 정산 건, 관리자 화면(all)에서는 전체 제출 건을 받습니다.
// 엑셀은 백엔드가 만듭니다 (domains/ledger): 지출 한 건이 한 줄, 정산 유형별 소계와 합계는 수식.

import { useState } from 'react'
import { downloadLedger } from '../api/client.js'

export default function LedgerButton({ all = false }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function run() {
    setBusy(true)
    setError('')
    try {
      await downloadLedger({ all })
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <span className="ledger-btn">
      {error && <span className="save-error" role="alert">{error}</span>}
      <button type="button" className="btn" onClick={run} disabled={busy} title={all ? '반려한 건을 뺀 전체 제출 건' : '반려된 건을 뺀 내 정산 건'}>
        {busy ? '만드는 중…' : '지출내역 엑셀 받기'}
      </button>
    </span>
  )
}
