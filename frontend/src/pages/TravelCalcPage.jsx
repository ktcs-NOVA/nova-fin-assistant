// U-05 출장비 계산 화면
// 출장 정보를 넣으면 백엔드(PM 의 travel_calc 엔진)가 여비규정 별표 1 기준으로 받을 수 있는 금액을
// 항목별 계산식·근거 조항과 함께 돌려줍니다. 요청·응답 모양은 docs/API.md 3-5, docs/U-05_출장비계산.md 그대로입니다.
//
// 결과의 verify_request 를 "청구 검증으로 보내기"로 넘기면 U-04 청구 검증 폼이 그 값으로 채워집니다.
// (App.jsx 의 sendToVerify → VerifyPage prefill)

import { useState } from 'react'
import { calcTravel } from '../api/client.js'
import DateRangePicker from '../components/DateRangePicker.jsx'
import RouteField from '../components/RouteField.jsx'

const TRIP_TYPES = ['국내출장', '근무지 내 출장']
const GRADES = ['직원 3급 이하', '직원 1·2급', '임원/본부장', '감사', '사장']
const REGIONS = ['', '서울', '광역시', '기타']
const VEHICLES = ['대중교통', '업무용차량', '렌트차량', '자가용']
const FARE_TYPES = ['철도', '항공', '버스', '선박']
const FUELS = ['휘발유', '경유', 'LPG', '하이브리드', '전기']
// 계산 방식(type)별 표시. PM 문서: 정액 / 상한(실비) / 실비 / 실비(한도) / 감액
const TYPE_HINT = {
  '정액': '그대로 지급',
  '상한(실비)': '영수증 금액, 이 금액까지',
  '실비': '입력한 운임',
  '실비(한도)': '유류비 계산, 대중교통 운임 한도',
  '감액': '지급 없음',
}

const seatOptions = (t) => (t === '철도' ? ['일반', '특실'] : t === '항공' ? ['이코노미', '비즈니스'] : null)
const won = (n) => (n == null ? '—' : `${Number(n).toLocaleString('ko-KR')}원`)
const emptyFare = () => ({ type: '철도', amount: '', seat_class: '' })

const INITIAL_TRIP = {
  start_date: '', end_date: '', region: '', vehicle: '대중교통',
  education: false, breakfast_nights: '', meals_provided: '', lodging_provided: false,
  hours: '', round_trip_km: '',
}
const INITIAL_CAR = { approved: false, distance_km: '', fuel: '휘발유', unit_price: '', tolls: '', public_fare: '' }

// PM 문서(docs/U-05_출장비계산.md)의 예시: 부산 1박 2일, KTX 일반실
const SAMPLE = {
  trip_type: '국내출장', grade: '직원 3급 이하',
  trip: { ...INITIAL_TRIP, start_date: '2026-10-20', end_date: '2026-10-21', region: '광역시', vehicle: '대중교통', breakfast_nights: '1' },
  fares: [{ type: '철도', amount: '59800', seat_class: '일반' }],
  car: { ...INITIAL_CAR },
}
// 자가용 예시: 사무실 → 출장지 왕복 200km, 휘발유
const SAMPLE_CAR = {
  trip_type: '국내출장', grade: '직원 3급 이하',
  trip: { ...INITIAL_TRIP, start_date: '2026-10-20', end_date: '2026-10-20', region: '기타', vehicle: '자가용' },
  fares: [],
  car: { approved: true, distance_km: '200', fuel: '휘발유', unit_price: '1700', tolls: '6000', public_fare: '45000' },
}

export default function TravelCalcPage({ onSendToVerify }) {
  const [tripType, setTripType] = useState('국내출장')
  const [grade, setGrade] = useState('직원 3급 이하')
  const [trip, setTrip] = useState(INITIAL_TRIP)
  const [fares, setFares] = useState([])
  const [car, setCar] = useState(INITIAL_CAR)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const intra = tripType.includes('근무지')
  const privateCar = trip.vehicle === '자가용'
  const electric = car.fuel === '전기'

  const editTrip = (k, v) => setTrip((t) => ({ ...t, [k]: v }))
  const editCar = (k, v) => setCar((c) => ({ ...c, [k]: v }))
  const editFare = (i, k, v) => setFares((list) => list.map((f, idx) => (idx === i ? { ...f, [k]: v } : f)))
  const addFare = () => setFares((list) => [...list, emptyFare()])
  const removeFare = (i) => setFares((list) => list.filter((_, idx) => idx !== i))

  // 경로 조회로 받은 편도 거리 → 자가용이면 왕복 운행거리(km)로 채움 (직접 고칠 수 있음)
  function applyDistance(oneWayKm) {
    if (privateCar && oneWayKm) editCar('distance_km', String(Math.round(oneWayKm * 2)))
  }

  function load(sample) {
    setTripType(sample.trip_type)
    setGrade(sample.grade)
    setTrip({ ...sample.trip })
    setFares(sample.fares.map((f) => ({ ...f })))
    setCar({ ...sample.car })
    setResult(null)
    setError('')
  }

  // 화면 값 → API.md 3-5 요청 JSON. 빈 칸은 보내지 않음.
  function buildRequest() {
    const t = {}
    if (intra) {
      if (trip.vehicle) t.vehicle = trip.vehicle
      if (trip.hours !== '') t.hours = Number(trip.hours)
      if (trip.round_trip_km !== '') t.round_trip_km = Number(trip.round_trip_km)
    } else {
      for (const k of ['start_date', 'end_date', 'region', 'vehicle']) if (trip[k]) t[k] = trip[k]
      if (trip.education) t.purpose = '교육'
      if (trip.breakfast_nights !== '') t.breakfast_nights = Number(trip.breakfast_nights)
      if (trip.meals_provided !== '') t.meals_provided = Number(trip.meals_provided)
      if (trip.lodging_provided) t.lodging_provided = true
      if (privateCar) t.private_car_approved = car.approved
    }
    const req = { trip_type: tripType, grade, trip: t }

    if (!intra) {
      const rows = fares.filter((f) => Number(f.amount) > 0).map((f) => {
        const row = { type: f.type, amount: Number(f.amount) }
        if (seatOptions(f.type) && f.seat_class) row.seat_class = f.seat_class
        return row
      })
      if (rows.length) req.fares = rows
      if (privateCar) {
        const c = { fuel: car.fuel }
        if (car.distance_km !== '') c.distance_km = Number(car.distance_km)
        if (car.unit_price !== '') c[electric ? 'price_per_kwh' : 'price_per_liter'] = Number(car.unit_price)
        if (car.tolls !== '') c.tolls = Number(car.tolls)
        if (car.public_fare !== '') c.public_fare = Number(car.public_fare)
        req.private_car = c
      }
    }
    return req
  }

  function validate() {
    if (!intra) {
      if (!trip.start_date || !trip.end_date) return '출장 시작일과 종료일을 입력해 주세요.'
      if (trip.end_date < trip.start_date) return '출장 종료일이 시작일보다 앞설 수 없습니다.'
      if (privateCar && car.distance_km === '') return '자가용 운행거리(km)를 입력해 주세요. 사무실에서 출장지까지 네이버 길찾기 기준입니다.'
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
      setResult(await calcTravel(buildRequest()))
    } catch (e) {
      setError(e.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  // 계산 결과 → U-04 청구 검증 폼 초기값. 금액은 계산된 한도이므로 직원이 실제 영수증 금액으로 고친 뒤 검증합니다.
  function sendToVerify() {
    const vr = result?.verify_request
    if (!vr) return
    const tripOut = {}
    for (const k of ['start_date', 'end_date', 'region', 'vehicle']) if (vr.trip?.[k]) tripOut[k] = vr.trip[k]
    onSendToVerify?.({
      from: 'travel',
      trip_type: vr.trip_type,
      grade: vr.grade,
      trip: tripOut,
      items: (vr.items ?? []).map((it) => ({
        field: it.field,
        amount: String(it.amount ?? ''),
        nights: it.nights ? String(it.nights) : '',
        breakfast_included: Boolean(it.breakfast_included),
        seat_class: it.seat_class ?? '',
      })),
    })
  }

  return (
    <section>
      <div className="page-title">
        <h1>출장비 계산</h1>
        <span className="desc">출장 정보를 넣으면 여비규정 별표 1 기준으로 받을 수 있는 금액을 항목별로 계산합니다.</span>
      </div>

      <div className="verify-layout">
        {/* ---------- 입력 ---------- */}
        <div className="verify-form">
          <div className="card">
            <div className="card-head">
              <h2>1. 기본 정보</h2>
              <div className="btn-row" style={{ margin: 0 }}>
                <button type="button" className="btn" onClick={() => load(SAMPLE)}>부산 1박 예시</button>
                <button type="button" className="btn" onClick={() => load(SAMPLE_CAR)}>자가용 예시</button>
              </div>
            </div>
            <div className="form-grid">
              <label className="field">
                <span className="field-label">출장 유형 *</span>
                <select value={tripType} onChange={(e) => setTripType(e.target.value)}>
                  {TRIP_TYPES.map((t) => <option key={t}>{t}</option>)}
                </select>
              </label>
              <label className="field">
                <span className="field-label">직급 * <em>일비·식비·숙박 상한</em></span>
                <select value={grade} onChange={(e) => setGrade(e.target.value)}>
                  {GRADES.map((g) => <option key={g}>{g}</option>)}
                </select>
              </label>
            </div>
          </div>

          {intra ? (
            <div className="card">
              <h2>2. 근무지 내 출장 정보</h2>
              <p className="hint">같은 시·군 안의 출장은 교통비만 지급됩니다 (4시간 이상 30,000원 / 미만 15,000원).</p>
              <div className="form-grid">
                <label className="field">
                  <span className="field-label">교통수단 <em>업무용 차량이면 0원</em></span>
                  <select value={trip.vehicle} onChange={(e) => editTrip('vehicle', e.target.value)}>
                    {VEHICLES.map((v) => <option key={v}>{v}</option>)}
                  </select>
                </label>
                <label className="field">
                  <span className="field-label">출장 시간(시간)</span>
                  <input type="number" min="0" step="0.5" value={trip.hours} placeholder="예: 5" onChange={(e) => editTrip('hours', e.target.value)} />
                </label>
                <label className="field">
                  <span className="field-label">왕복 거리(km) <em>8km 미만은 0원</em></span>
                  <input type="number" min="0" value={trip.round_trip_km} placeholder="예: 12" onChange={(e) => editTrip('round_trip_km', e.target.value)} />
                </label>
              </div>
            </div>
          ) : (
            <>
              <div className="card">
                <h2>2. 출장 기간 *</h2>
                <p className="hint">달력에서 출발일과 도착일을 차례로 눌러 고르세요.</p>
                <DateRangePicker
                  start={trip.start_date}
                  end={trip.end_date}
                  onChange={({ start, end }) => setTrip((t) => ({ ...t, start_date: start, end_date: end }))}
                />
              </div>

              <div className="card">
                <h2>3. 경로</h2>
                <RouteField onDistance={applyDistance} />
              </div>

              <div className="card">
                <h2>4. 출장 정보</h2>
                <div className="form-grid">
                  <label className="field">
                    <span className="field-label">출장지 지역 <em>숙박비 상한</em></span>
                    <select value={trip.region} onChange={(e) => editTrip('region', e.target.value)}>
                      {REGIONS.map((r) => <option key={r} value={r}>{r || '선택 안 함'}</option>)}
                    </select>
                  </label>
                  <label className="field">
                    <span className="field-label">교통수단 <em>일비·자가용 규칙</em></span>
                    <select value={trip.vehicle} onChange={(e) => editTrip('vehicle', e.target.value)}>
                      {VEHICLES.map((v) => <option key={v}>{v}</option>)}
                    </select>
                  </label>
                  <label className="field">
                    <span className="field-label">조식 포함 숙박 박수 <em>1박당 식비 1/3 차감</em></span>
                    <input type="number" min="0" value={trip.breakfast_nights} placeholder="0" onChange={(e) => editTrip('breakfast_nights', e.target.value)} />
                  </label>
                  <label className="field">
                    <span className="field-label">주최 측 제공 식사 수 <em>1식당 식비 1/3 차감</em></span>
                    <input type="number" min="0" value={trip.meals_provided} placeholder="0" onChange={(e) => editTrip('meals_provided', e.target.value)} />
                  </label>
                  <label className="field field-check">
                    <span className="field-label">교육 출장 <em>일비 2일 한도</em></span>
                    <span className="check-inline">
                      <input type="checkbox" checked={trip.education} onChange={(e) => editTrip('education', e.target.checked)} />
                      근무지 외 교육 참석
                    </span>
                  </label>
                  <label className="field field-check">
                    <span className="field-label">숙박 무료 제공 <em>숙박비 전액 감액</em></span>
                    <span className="check-inline">
                      <input type="checkbox" checked={trip.lodging_provided} onChange={(e) => editTrip('lodging_provided', e.target.checked)} />
                      주최 측이 숙소를 제공함
                    </span>
                  </label>
                </div>
              </div>

              <div className="card">
                <div className="card-head">
                  <h2>5. 교통 운임 <span className="hint">(선택)</span></h2>
                  <button type="button" className="btn" onClick={addFare}>+ 운임 추가</button>
                </div>
                <p className="hint">이미 알고 있는 기차·항공·버스 요금을 넣으면 실비로 합산됩니다. 자가용은 아래에서 따로 계산합니다.</p>
                {fares.map((f, i) => (
                  <div key={i} className="item-row">
                    <div className="form-grid">
                      <label className="field">
                        <span className="field-label">교통수단</span>
                        <select value={f.type} onChange={(e) => editFare(i, 'type', e.target.value)}>
                          {FARE_TYPES.map((t) => <option key={t}>{t}</option>)}
                        </select>
                      </label>
                      <label className="field">
                        <span className="field-label">운임(원)</span>
                        <input type="number" min="0" value={f.amount} placeholder="0" onChange={(e) => editFare(i, 'amount', e.target.value)} />
                      </label>
                      {seatOptions(f.type) && (
                        <label className="field">
                          <span className="field-label">좌석 등급 <em>직급별 좌석 규칙</em></span>
                          <select value={f.seat_class} onChange={(e) => editFare(i, 'seat_class', e.target.value)}>
                            <option value="">선택 안 함</option>
                            {seatOptions(f.type).map((o) => <option key={o}>{o}</option>)}
                          </select>
                        </label>
                      )}
                    </div>
                    <button type="button" className="btn item-remove" onClick={() => removeFare(i)} aria-label="운임 삭제">삭제</button>
                  </div>
                ))}
              </div>

              {privateCar && (
                <div className="card">
                  <h2>6. 자가용 정보</h2>
                  <p className="hint">
                    연료비 = 운행거리 ÷ 연비 × 출장 당일 단가 (실무자 의견 반영 산식). 운행거리는 <b>사무실(근무지)</b>에서 출장지까지 네이버 길찾기 km 기준이며 집 출발은 인정되지 않습니다.
                    연료비 + 통행료는 같은 구간 철도·버스 운임을 넘을 수 없습니다.
                  </p>
                  <div className="form-grid">
                    <label className="field">
                      <span className="field-label">운행거리(km, 왕복) *</span>
                      <input type="number" min="0" value={car.distance_km} placeholder="예: 200" onChange={(e) => editCar('distance_km', e.target.value)} />
                    </label>
                    <label className="field">
                      <span className="field-label">연료 구분 <em>연비 9·7·6·15 km/L, 전기 3.5 km/kWh</em></span>
                      <select value={car.fuel} onChange={(e) => editCar('fuel', e.target.value)}>
                        {FUELS.map((f) => <option key={f}>{f}</option>)}
                      </select>
                    </label>
                    <label className="field">
                      <span className="field-label">출장일 {electric ? '충전단가(원/kWh)' : '유류단가(원/L)'} <em>비우면 가정값</em></span>
                      <input type="number" min="0" value={car.unit_price} placeholder={electric ? '예: 350' : '예: 1700'} onChange={(e) => editCar('unit_price', e.target.value)} />
                    </label>
                    <label className="field">
                      <span className="field-label">통행료(원) <em>영수증 기준</em></span>
                      <input type="number" min="0" value={car.tolls} placeholder="0" onChange={(e) => editCar('tolls', e.target.value)} />
                    </label>
                    <label className="field">
                      <span className="field-label">같은 구간 철도·버스 운임(원) <em>한도</em></span>
                      <input type="number" min="0" value={car.public_fare} placeholder="예: 59800" onChange={(e) => editCar('public_fare', e.target.value)} />
                    </label>
                    <label className="field field-check">
                      <span className="field-label">출장승인권자 승인 <em>제13조 제5항</em></span>
                      <span className="check-inline">
                        <input type="checkbox" checked={car.approved} onChange={(e) => editCar('approved', e.target.checked)} />
                        부득이한 사유로 자가용 이용을 승인받음
                      </span>
                    </label>
                  </div>
                </div>
              )}
            </>
          )}

          <div className="btn-row">
            <button type="button" className="btn primary" onClick={run} disabled={loading}>
              {loading ? '계산 중…' : '계산하기'}
            </button>
          </div>
        </div>

        {/* ---------- 결과 ---------- */}
        <div className="verify-result">
          {error && <div className="error">{error}</div>}
          {result ? (
            <CalcResult result={result} onSendToVerify={onSendToVerify ? sendToVerify : null} />
          ) : (
            !loading && <div className="empty">출장 정보를 입력하고 "계산하기"를 누르면 항목별 금액과 계산식이 여기에 표시됩니다.</div>
          )}
        </div>
      </div>
    </section>
  )
}

function CalcResult({ result, onSendToVerify }) {
  const { summary = {}, lines = [], notes = [] } = result
  const meta = [result.grade, result.region, result.days ? `${result.days}일` : null, result.nights ? `${result.nights}박` : null].filter(Boolean)
  return (
    <div className="result">
      <div className="calc-total">
        <span className="label">받을 수 있는 금액 (예상 최대)</span>
        <strong>{won(summary.estimated_max)}</strong>
        <span className="calc-meta">{meta.join(' · ')}</span>
      </div>
      <div className="stat-row">
        <div className="stat"><span className="stat-label">정액 (일비+식비)</span><span className="stat-value">{won(summary.fixed_total)}</span></div>
        <div className="stat"><span className="stat-label">숙박비 상한</span><span className="stat-value">{won(summary.lodging_cap)}</span></div>
        <div className="stat"><span className="stat-label">교통비</span><span className="stat-value">{won(summary.transport_total)}</span></div>
      </div>

      <div className="result-list">
        {lines.map((l, i) => (
          <div key={`${l.field}-${i}`} className="card calc-line">
            <div className="calc-line-head">
              <b>{l.field}</b>
              <span className={`badge type-${l.type.replace(/[()]/g, '')}`} title={TYPE_HINT[l.type] ?? ''}>{l.type}</span>
              <span className="calc-amount">{won(l.amount)}</span>
            </div>
            <div className="calc-formula">{l.formula}</div>
            <div className="calc-basis">근거: {l.basis}</div>
            {l.note && <div className="hint">{l.note}</div>}
          </div>
        ))}
      </div>

      {notes.length > 0 && (
        <ul className="notes-box">
          {notes.map((n, i) => <li key={i}>{n}</li>)}
        </ul>
      )}

      {onSendToVerify && (
        <div className="btn-row">
          <button type="button" className="btn primary" onClick={onSendToVerify}>청구 검증으로 보내기 →</button>
        </div>
      )}
      <p className="hint">숙박비는 계산된 상한이 들어갑니다. 청구 검증에서 실제 영수증 금액으로 고친 뒤 검증하세요.</p>
    </div>
  )
}
