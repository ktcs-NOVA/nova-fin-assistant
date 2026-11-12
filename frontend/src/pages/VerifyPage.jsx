// U-04 청구 검증 화면
// 입력 폼은 PM 문서 docs/U-04_청구검증_입력필드.md 의 "0. 최소 세트" 기준입니다.
//   기본 정보: 청구 유형, 직급
//   출장 정보 (출장일 때만): 시작일, 종료일, 출장지 지역, 교통수단
//   청구 항목 (행 추가): 항목명, 금액, 사용일, 메모 + 숙박비면 박수·조식 포함, 철도·항공이면 좌석 등급
// 요청 JSON 모양은 docs/API.md 3-2 그대로이고, 선택 칸은 값이 있을 때만 보냅니다.
//
// prefill: 다른 화면에서 "청구 검증으로 보내기"로 넘어온 초기값 ({ from, trip_type, grade?, trip?, items }).
//   - 영수증 등록(U-06, from: 'receipt'): 항목에 가맹점·업종·사용 시각·결제수단(법인카드)이 함께 오고, 화면엔 읽기 전용으로 보여 주며 요청에 그대로 실립니다.
//   - 출장비 계산(U-05, from: 'travel'): 직급·출장 정보와 계산된 항목(일비·식비·숙박비 상한·운임)이 옵니다. 숙박비는 상한이므로 실제 금액으로 고쳐 검증합니다.

import { useState } from 'react'
import { verifyClaim } from '../api/client.js'
import VerifyResult from '../components/VerifyResult.jsx'
import SubmitPanel from '../components/SubmitPanel.jsx'

const TRIP_TYPES = ['국내출장', '근무지 내 출장', '법인카드', '업무추진비']
const GRADES = ['직원 3급 이하', '직원 1·2급', '임원/본부장', '감사', '사장']
const REGIONS = ['', '서울', '광역시', '기타']
const VEHICLES = ['', '대중교통', '업무용차량', '렌트차량', '자가용']
// 항목명 추천값 (PM 문서 3-1). 직접 입력도 가능.
const FIELD_NAMES = ['교통비', '철도운임', '항공운임', '숙박비', '식비', '일비', '통행료·주차비', '회의 식대', '업무추진비', '부서운영비', '경조금', '화환', '기타']

const isTrip = (t) => t.includes('출장')
const isLodging = (f) => f.includes('숙박')
// 좌석 등급이 붙는 항목: 철도(일반/특실), 항공(이코노미/비즈니스)
const seatOptions = (f) => (f.includes('철도') || f.includes('KTX') ? ['일반', '특실'] : f.includes('항공') ? ['이코노미', '비즈니스'] : null)
const today = () => new Date().toISOString().slice(0, 10)

const emptyItem = () => ({
  field: '', amount: '', date: '', note: '', nights: '', breakfast_included: false, seat_class: '', exception_reason: '',
  // 영수증에서 넘어올 때만 채워지는 칸 (PM 엔진의 법인카드 규칙용)
  merchant: '', merchant_type: '', time: '', payment: '', receipt_file: '',
})
const fromReceipt = (it) => Boolean(it.receipt_file)

// PM 문서 6절의 출장 시연 시나리오 (버튼 한 번으로 채움)
const SAMPLE = {
  trip_type: '국내출장',
  grade: '직원 3급 이하',
  trip: { start_date: '2026-10-20', end_date: '2026-10-21', region: '광역시', vehicle: '대중교통' },
  items: [
    { field: '철도운임', amount: '59800', date: '2026-10-20', note: '', nights: '', breakfast_included: false, seat_class: '특실' },
    { field: '숙박비', amount: '98000', date: '2026-10-20', note: '', nights: '1', breakfast_included: true, seat_class: '' },
    { field: '식비', amount: '54000', date: '', note: '', nights: '', breakfast_included: false, seat_class: '' },
    { field: '일비', amount: '60000', date: '', note: '', nights: '', breakfast_included: false, seat_class: '' },
  ],
}

export default function VerifyPage({ prefill }) {
  const [tripType, setTripType] = useState(prefill?.trip_type ?? '국내출장')
  const [grade, setGrade] = useState(prefill?.grade ?? '직원 3급 이하')
  const [trip, setTrip] = useState({ start_date: '', end_date: '', region: '', vehicle: '', ...(prefill?.trip ?? {}) })
  const [items, setItems] = useState(() => (prefill?.items?.length ? prefill.items.map((it) => ({ ...emptyItem(), ...it })) : [emptyItem()]))
  const receiptCount = items.filter(fromReceipt).length
  const fromTravel = prefill?.from === 'travel' && items.length > 0
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const editTrip = (k, v) => setTrip((t) => ({ ...t, [k]: v }))
  const editItem = (i, k, v) => setItems((list) => list.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)))
  const addItem = () => setItems((list) => [...list, emptyItem()])
  const removeItem = (i) => setItems((list) => (list.length > 1 ? list.filter((_, idx) => idx !== i) : list))

  function loadSample() {
    setTripType(SAMPLE.trip_type)
    setGrade(SAMPLE.grade)
    setTrip(SAMPLE.trip)
    setItems(SAMPLE.items.map((it) => ({ ...it })))
    setResult(null)
    setError('')
  }

  // 화면 값 → API.md 3-2 요청 JSON. 빈 선택 칸은 보내지 않음.
  function buildRequest() {
    const req = { trip_type: tripType, grade, settlement_date: today(), items: [] }
    if (isTrip(tripType)) {
      const t = {}
      for (const [k, v] of Object.entries(trip)) if (v) t[k] = v
      if (Object.keys(t).length) req.trip = t
    }
    for (const it of items) {
      const row = { field: it.field.trim(), amount: Number(it.amount) }
      if (it.date) row.date = it.date
      if (it.note.trim()) row.note = it.note.trim()
      if (isLodging(it.field)) {
        if (it.nights) row.nights = Number(it.nights)
        row.breakfast_included = it.breakfast_included
        // 숙박 상한 초과 시 특례 사유 (여비규정 제11조⑥) — 있으면 담당자 확인으로 판정됨
        if (it.exception_reason.trim()) row.exception_reason = it.exception_reason.trim()
      }
      if (seatOptions(it.field) && it.seat_class) row.seat_class = it.seat_class
      // 영수증에서 온 항목: 가맹점·업종·시각·결제수단을 그대로 실어 법인카드 규칙(심야·제한업종)을 받게 함
      for (const k of ['merchant', 'merchant_type', 'time', 'payment']) if (it[k]) row[k] = it[k]
      req.items.push(row)
    }
    return req
  }

  function validate() {
    const bad = items.findIndex((it) => !it.field.trim() || !(Number(it.amount) > 0))
    if (bad >= 0) return `${bad + 1}번째 항목의 항목명과 금액을 입력해 주세요.`
    if (isTrip(tripType) && trip.start_date && trip.end_date && trip.end_date < trip.start_date) {
      return '출장 종료일이 시작일보다 앞설 수 없습니다.'
    }
    return ''
  }

  async function run() {
    const msg = validate()
    if (msg) {
      setError(msg)
      return
    }
    setLoading(true)
    setError('')
    try {
      setResult(await verifyClaim(buildRequest()))
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

      <div className="verify-layout">
        {/* ---------- 입력 ---------- */}
        <div className="verify-form">
          {receiptCount > 0 && (
            <div className="notice">
              영수증 등록에서 {receiptCount}건을 넘겨받았습니다. 결제수단은 법인카드로 채웠고, 필요하면 항목을 더 넣은 뒤 "검증하기"를 누르세요.
            </div>
          )}
          {fromTravel && (
            <div className="notice">
              출장비 계산 결과 {items.length}건을 넘겨받았습니다. 숙박비는 규정 상한이 들어가 있으니 실제 영수증 금액으로 고친 뒤 "검증하기"를 누르세요.
            </div>
          )}
          <div className="card">
            <div className="card-head">
              <h2>1. 청구 기본 정보</h2>
              <button type="button" className="btn" onClick={loadSample}>출장 예시 불러오기</button>
            </div>
            <div className="form-grid">
              <label className="field">
                <span className="field-label">청구 유형 *</span>
                <select value={tripType} onChange={(e) => setTripType(e.target.value)}>
                  {TRIP_TYPES.map((t) => <option key={t}>{t}</option>)}
                </select>
              </label>
              <label className="field">
                <span className="field-label">직급 *</span>
                <select value={grade} onChange={(e) => setGrade(e.target.value)}>
                  {GRADES.map((g) => <option key={g}>{g}</option>)}
                </select>
              </label>
            </div>
          </div>

          {isTrip(tripType) && (
            <div className="card">
              <h2>2. 출장 정보</h2>
              <p className="hint">비워 두면 해당 규칙은 건너뛰거나 "담당자 확인 필요"로 안내됩니다.</p>
              <div className="form-grid">
                <label className="field">
                  <span className="field-label">출장 시작일</span>
                  <input type="date" value={trip.start_date} onChange={(e) => editTrip('start_date', e.target.value)} />
                </label>
                <label className="field">
                  <span className="field-label">출장 종료일</span>
                  <input type="date" value={trip.end_date} onChange={(e) => editTrip('end_date', e.target.value)} />
                </label>
                <label className="field">
                  <span className="field-label">출장지 지역 <em>숙박비 상한 판단</em></span>
                  <select value={trip.region} onChange={(e) => editTrip('region', e.target.value)}>
                    {REGIONS.map((r) => <option key={r} value={r}>{r || '선택 안 함'}</option>)}
                  </select>
                </label>
                <label className="field">
                  <span className="field-label">교통수단 <em>일비·자가용 규칙</em></span>
                  <select value={trip.vehicle} onChange={(e) => editTrip('vehicle', e.target.value)}>
                    {VEHICLES.map((v) => <option key={v} value={v}>{v || '선택 안 함'}</option>)}
                  </select>
                </label>
              </div>
            </div>
          )}

          <div className="card">
            <h2>{isTrip(tripType) ? '3' : '2'}. 청구 항목</h2>
            <div className="items-editor">
              {items.map((it, i) => (
                <div key={i} className={`item-row ${fromReceipt(it) ? 'from-receipt' : ''}`}>
                  {fromReceipt(it) && (
                    <div className="item-origin">
                      <span className="badge muted">영수증</span>
                      <span>{it.merchant}{it.merchant_type ? ` · ${it.merchant_type}` : ''}{it.time ? ` · ${it.time}` : ''} · {it.payment}</span>
                    </div>
                  )}
                  <div className="form-grid">
                    <label className="field">
                      <span className="field-label">항목명 *</span>
                      <input list="field-names" value={it.field} placeholder="예: 숙박비" onChange={(e) => editItem(i, 'field', e.target.value)} />
                    </label>
                    <label className="field">
                      <span className="field-label">금액(원) *</span>
                      <input type="number" min="0" value={it.amount} placeholder="0" onChange={(e) => editItem(i, 'amount', e.target.value)} />
                    </label>
                    <label className="field">
                      <span className="field-label">사용일</span>
                      <input type="date" value={it.date} onChange={(e) => editItem(i, 'date', e.target.value)} />
                    </label>
                    <label className="field">
                      <span className="field-label">메모</span>
                      <input type="text" value={it.note} placeholder="예: 특실, 동승" onChange={(e) => editItem(i, 'note', e.target.value)} />
                    </label>
                    {seatOptions(it.field) && (
                      <label className="field">
                        <span className="field-label">좌석 등급 <em>직급별 좌석 규칙</em></span>
                        <select value={it.seat_class} onChange={(e) => editItem(i, 'seat_class', e.target.value)}>
                          <option value="">선택 안 함</option>
                          {seatOptions(it.field).map((o) => <option key={o} value={o}>{o}</option>)}
                        </select>
                      </label>
                    )}
                    {isLodging(it.field) && (
                      <>
                        <label className="field">
                          <span className="field-label">박수</span>
                          <input type="number" min="1" value={it.nights} placeholder="1" onChange={(e) => editItem(i, 'nights', e.target.value)} />
                        </label>
                        <label className="field field-check">
                          <span className="field-label">조식 포함 <em>식비 1/3 차감</em></span>
                          <span className="check-inline">
                            <input type="checkbox" checked={it.breakfast_included} onChange={(e) => editItem(i, 'breakfast_included', e.target.checked)} />
                            숙박에 조식이 포함됨
                          </span>
                        </label>
                        <label className="field">
                          <span className="field-label">특례 사유 <em>상한 초과 시</em></span>
                          <input type="text" value={it.exception_reason} placeholder="예: 행사 기간 숙소 부족" onChange={(e) => editItem(i, 'exception_reason', e.target.value)} />
                        </label>
                      </>
                    )}
                  </div>
                  <button type="button" className="btn item-remove" onClick={() => removeItem(i)} disabled={items.length === 1} aria-label="항목 삭제">
                    삭제
                  </button>
                </div>
              ))}
            </div>
            <datalist id="field-names">
              {FIELD_NAMES.map((f) => <option key={f} value={f} />)}
            </datalist>
            <div className="btn-row between">
              <button type="button" className="btn" onClick={addItem}>+ 항목 추가</button>
              <button type="button" className="btn primary" onClick={run} disabled={loading}>
                {loading ? '검증 중…' : '검증하기'}
              </button>
            </div>
          </div>
        </div>

        {/* ---------- 결과 ---------- */}
        <div className="verify-result">
          {error && <div className="error">{error}</div>}
          {result ? (
            <>
              <VerifyResult result={result} />
              <SubmitPanel claim={buildRequest()} result={result} />
            </>
          ) : (
            !loading && <div className="empty">청구 내역을 입력하고 "검증하기"를 누르면 항목별 판정이 여기에 표시됩니다.</div>
          )}
        </div>
      </div>
    </section>
  )
}
