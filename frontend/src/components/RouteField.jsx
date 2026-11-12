// 경로: 출발지는 회사로 고정이고, 도착지만 검색해서 거리를 가져옵니다. (네이버 지도 API — 서버에서 호출)
// 조회가 안 되는 환경(백엔드에 경로 API가 아직 없을 때)에서는 안내만 띄우고, 거리는 아래 입력칸에 직접 적으면 됩니다.

import { useState } from 'react'
import { lookupRoute, USE_MOCK } from '../api/client.js'

export const ORIGIN = '한국해양진흥공사 본사'

export default function RouteField({ onDistance }) {
  const [dest, setDest] = useState('')
  const [route, setRoute] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function search(e) {
    e.preventDefault()
    if (!dest.trim()) { setError('도착지를 입력해 주세요.'); return }
    setLoading(true); setError('')
    try {
      const r = await lookupRoute(dest.trim())
      setRoute(r)
      onDistance?.(r.distance_km)
    } catch {
      setRoute(null)
      setError('경로 조회가 아직 연결되지 않았어요. 거리(km)는 직접 입력해 주세요.')
    } finally { setLoading(false) }
  }

  return (
    <div className="route">
      <div className="route-origin"><span className="hint">출발</span><b>{ORIGIN} (고정)</b></div>
      <form className="route-search" onSubmit={search}>
        <label className="field">
          <span className="field-label">도착지 검색</span>
          <input type="text" value={dest} placeholder="예: 부산시청, 대전 정부청사" onChange={(e) => { setDest(e.target.value); setError('') }} />
        </label>
        <button type="submit" className="btn" disabled={loading}>{loading ? '조회 중…' : '경로 조회'}</button>
      </form>
      {error && <p className="login-error" role="alert">{error}</p>}
      {route && (
        <dl className="cal-summary">
          <div><dt>도착지</dt><dd>{route.destination}</dd></div>
          <div><dt>편도 거리</dt><dd>약 {route.distance_km} km</dd></div>
        </dl>
      )}
      <p className="hint">{USE_MOCK ? '목업 모드의 거리는 예시예요. ' : ''}거리와 경로는 네이버 지도 API로 가져와요. 자가용을 고르면 왕복 거리로 운행거리가 채워져요.</p>
    </div>
  )
}
