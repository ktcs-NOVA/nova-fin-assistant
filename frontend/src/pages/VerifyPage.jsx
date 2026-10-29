// 청구 검증 화면
// 지금은 "예시 청구로 검증" 버튼으로 흐름(요청 → 로딩 → 결과 카드)만 보여줍니다.
// 실제 입력 폼은 이 위에 기능으로 얹습니다.

import { useState } from 'react'
import { verifyClaim } from '../api/client.js'
import VerifyResult from '../components/VerifyResult.jsx'

// 예시 청구 (조율 문서 3-2 의 요청 모양)
const SAMPLE_CLAIM = {
  trip_type: '국내출장',
  grade: '직원 3급 이하',
  items: [
    { field: '식비', amount: 27000, date: '2026-10-20', note: '조식 포함 숙박' },
    { field: '숙박비', amount: 80000, date: '2026-10-20', note: '' },
  ],
}

export default function VerifyPage() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function run() {
    setLoading(true)
    setError('')
    try {
      setResult(await verifyClaim(SAMPLE_CLAIM))
    } catch (e) {
      setError(e.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section>
      <div className="page-title">
        <h1>청구 검증</h1>
        <span className="desc">제출 전 청구 내역을 규정 기준으로 점검합니다.</span>
      </div>

      <div className="toolbar">
        <button className="btn primary" onClick={run} disabled={loading}>
          {loading ? '검증 중…' : '예시 청구로 검증'}
        </button>
        <span className="hint">입력 폼은 다음 단계에서 추가됩니다.</span>
      </div>

      {error && <div className="error">{error}</div>}

      {result ? (
        <VerifyResult result={result} />
      ) : (
        !loading && <div className="empty">검증 버튼을 누르면 결과가 여기에 표시됩니다.</div>
      )}
    </section>
  )
}
