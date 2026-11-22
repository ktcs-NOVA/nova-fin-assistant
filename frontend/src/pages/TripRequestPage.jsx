// 출장 신청: 출장 전에 목적·기간·장소·교통을 등록합니다. (2026-11-20 코칭: 신청 → 정산 → 보고서 흐름)
//   1 목적 → 2 기간 → 3 장소·교통 → 4 확인 → 신청 완료(예상 출장비 · 출장 전에 챙길 것)
// 여기서 넣은 값은 다녀와서 '출장 정산'을 시작할 때 그대로 불러와 잠기고, 출장보고서의 목적·일시·장소로 이어집니다.
// 요청·응답 모양은 docs/API.md 3-15.

import { useState } from 'react'
import { calcTravel, createTrip } from '../api/client.js'
import DateRangePicker from '../components/DateRangePicker.jsx'
import RouteField from '../components/RouteField.jsx'
import WizardSteps from '../components/WizardSteps.jsx'
import { periodText } from '../utils/trips.js'

const STEPS = ['목적', '기간', '장소·교통', '확인']
const TRIP_TYPES = ['국내출장', '근무지 내 출장']
const VEHICLES = ['대중교통', '업무용차량', '렌트차량', '자가용']
const won = (n) => `${Number(n || 0).toLocaleString('ko-KR')}원`

const EMPTY = {
  trip_type: '국내출장', purpose: '', start_date: '', end_date: '',
  destination: '', distance_km: '', vehicle: '대중교통', private_car_approved: false,
  education: false, hours: '',
}

export default function TripRequestPage({ user, onNavigate }) {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(null)          // 신청 결과 (서버가 정한 지역 구분 포함)
  const [estimate, setEstimate] = useState(null)  // 예상 출장비 (출장비 계산 API)

  const edit = (k, v) => { setForm((f) => ({ ...f, [k]: v })); setError('') }
  const go = (n) => { setStep(n); setError(''); window.scrollTo?.(0, 0) }
  const privateCar = form.vehicle === '자가용'
  const intra = form.trip_type === '근무지 내 출장'
  const grade = user?.grade ?? '직원 3급 이하'

  function check(n) {
    if (n === 1 && !form.purpose.trim()) return '출장 목적을 적어 주세요. 출장보고서의 목적 칸에 그대로 들어가요.'
    if (n === 2 && (!form.start_date || !form.end_date)) return '달력에서 출발일과 돌아오는 날을 골라 주세요.'
    if (n === 3 && !form.destination.trim()) return '출장지를 적어 주세요. 경로 조회를 하면 자동으로 채워져요.'
    return ''
  }

  function next() {
    const msg = check(step)
    if (msg) { setError(msg); return }
    go(step + 1)
  }

  async function submit() {
    setSaving(true)
    setError('')
    try {
      const trip = await createTrip({
        trip_type: form.trip_type,
        purpose: form.purpose.trim(),
        destination: form.destination.trim(),
        start_date: form.start_date,
        end_date: form.end_date,
        vehicle: form.vehicle,
        private_car_approved: privateCar && form.private_car_approved,
        education: !intra && form.education,
        ...(form.distance_km !== '' ? { distance_km: Number(form.distance_km) } : {}),
        ...(intra && form.hours !== '' ? { hours: Number(form.hours) } : {}),
      })
      setDone(trip)
      window.scrollTo?.(0, 0)
      // 예상 출장비: 일비·식비·숙박 상한만 (운임은 다녀와서 실제 금액으로 정산)
      if (trip.trip_type === '국내출장') {
        const t = { start_date: trip.start_date, end_date: trip.end_date, vehicle: trip.vehicle === '자가용' ? '대중교통' : trip.vehicle }
        if (trip.region) t.region = trip.region
        if (trip.education) t.purpose = '교육'   // 일비 2일 한도
        calcTravel({ trip_type: '국내출장', grade, trip: t }).then(setEstimate).catch(() => setEstimate(null))
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  function restart() {
    setForm(EMPTY)
    setDone(null)
    setEstimate(null)
    go(1)
  }

  if (done) {
    const lines = (estimate?.lines ?? []).filter((l) => l.amount > 0)
    const lodging = lines.find((l) => l.field.includes('숙박'))
    const fixed = lines.filter((l) => l.type === '정액')
    return (
      <section className="wizard">
        <div className="page-title">
          <h1>출장 신청</h1>
          <span className="desc">다녀온 뒤 홈의 ‘내 출장’에서 바로 정산할 수 있어요.</span>
        </div>
        <div className="card wiz-card">
          <p className="notice wiz-banner">✓ 출장 신청 완료 · {done.stage}</p>
          <dl className="cal-summary trip-summary">
            <div><dt>목적</dt><dd>{done.purpose}</dd></div>
            <div><dt>기간</dt><dd>{periodText(done.start_date, done.end_date)}</dd></div>
            <div><dt>출장지</dt><dd>{done.destination}{done.region ? ` (${done.region})` : ''}</dd></div>
            <div><dt>교통</dt><dd>{done.vehicle}{done.distance_km ? ` · 편도 약 ${done.distance_km} km` : ''}</dd></div>
          </dl>

          {lines.length > 0 && (
            <>
              <h3 className="wiz-sub">예상 출장비 <span className="hint">({grade} 기준)</span></h3>
              <ul className="trip-est">
                {lines.map((l) => (
                  <li key={l.field}>
                    <span className="trip-est-name">{l.field}</span>
                    <b>{won(l.amount)}</b>
                    <span className="hint">{l.type === '정액' ? '정액 지급' : '이 금액까지 실비'} · {l.basis}</span>
                  </li>
                ))}
              </ul>
              <p className="hint">교통비는 다녀와서 실제 운임(영수증) 금액으로 정산해요.</p>
            </>
          )}

          <h3 className="wiz-sub">출장 전에 챙길 것</h3>
          <ul className="trip-todo">
            {done.vehicle === '대중교통' && <li>KTX·항공권 예매 — 승차권과 결제 영수증은 정산할 때 필요해요.</li>}
            {done.vehicle === '자가용' && !done.private_car_approved && (
              <li><b>자가용 사용 사전 승인 받기</b> — 승인이 없으면 유류비 대신 대중교통 운임 기준으로 정산될 수 있어요.</li>
            )}
            {done.vehicle === '자가용' && <li>통행료·주유 영수증 챙기기 — 운행거리는 신청한 경로 거리로 채워져요.</li>}
            {done.start_date !== done.end_date && (
              <li>숙소 예약{lodging ? ` — 이번 출장은 ${won(lodging.amount)}까지 실비로 받아요.` : ''} 숙박 청구서와 카드 영수증을 받아 두세요.</li>
            )}
            {fixed.length > 0 && <li>{fixed.map((l) => `${l.field} ${won(l.amount)}`).join(' · ')}은 정액이라 영수증 없이 지급돼요.</li>}
            <li>다녀오면 홈 ‘내 출장’에서 <b>정산하기</b>를 누르세요. 신청한 목적·기간·장소가 그대로 채워져요.</li>
          </ul>

          <div className="wiz-nav">
            <button type="button" className="btn" onClick={restart}>다른 출장 신청</button>
            <button type="button" className="btn primary" onClick={() => onNavigate('home')}>홈으로</button>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="wizard">
      <div className="page-title">
        <h1>출장 신청</h1>
        <span className="desc">출장 전에 한 번만 적어 두면, 정산과 출장보고서에 그대로 이어져요.</span>
      </div>

      <WizardSteps steps={STEPS} current={step} />

      {step === 1 && (
        <div className="card wiz-card">
          <h2>어떤 출장인가요?</h2>
          <div className="segmented trip-seg" role="group" aria-label="출장 구분">
            {TRIP_TYPES.map((t) => (
              <button key={t} type="button" className={form.trip_type === t ? 'on' : ''} onClick={() => edit('trip_type', t)}>{t}</button>
            ))}
          </div>
          {intra && <p className="hint">같은 시·군 안의 출장이에요. 교통비만 지급돼요.</p>}
          <label className="field">
            <span className="field-label">출장 목적 * <em>출장보고서 목적 칸에 들어가요</em></span>
            <input type="text" value={form.purpose} maxLength={200} placeholder="예: 부산 선사 방문 · 선박금융 상담" onChange={(e) => edit('purpose', e.target.value)} />
          </label>
          {!intra && (
            <label className="check-inline">
              <input type="checkbox" checked={form.education} onChange={(e) => edit('education', e.target.checked)} />
              교육 출장이에요 (근무지 외 교육 참석 · 일비는 2일까지)
            </label>
          )}
        </div>
      )}

      {step === 2 && (
        <div className="card wiz-card">
          <h2>언제 다녀오시나요?</h2>
          <p className="hint">출발일과 돌아오는 날을 차례로 눌러 주세요. 당일 출장이면 같은 날을 한 번 더 누르면 돼요.</p>
          <DateRangePicker
            blockWeekends
            start={form.start_date}
            end={form.end_date}
            onChange={({ start, end }) => setForm((f) => ({ ...f, start_date: start, end_date: end }))}
          />
        </div>
      )}

      {step === 3 && (
        <div className="card wiz-card">
          <h2>어디로, 무엇을 타고 가시나요?</h2>
          <RouteField onDistance={(km, r) => setForm((f) => ({ ...f, distance_km: km ?? '', destination: r?.destination || f.destination }))} />
          <div className="form-grid">
            <label className="field">
              <span className="field-label">출장지 * <em>출장보고서에 들어가요</em></span>
              <input type="text" value={form.destination} maxLength={100} placeholder="예: 부산 강서구 부산항 신항" onChange={(e) => edit('destination', e.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">편도 거리(km) <em>경로 조회로 채워져요</em></span>
              <input type="number" min="0" value={form.distance_km} placeholder="예: 330" onChange={(e) => edit('distance_km', e.target.value)} />
            </label>
            {intra && (
              <label className="field">
                <span className="field-label">예상 출장 시간(시간) <em>4시간 이상이면 교통비 30,000원</em></span>
                <input type="number" min="0" max="24" step="0.5" value={form.hours} placeholder="예: 5" onChange={(e) => edit('hours', e.target.value)} />
              </label>
            )}
            <label className="field">
              <span className="field-label">교통수단</span>
              <select value={form.vehicle} onChange={(e) => edit('vehicle', e.target.value)}>
                {VEHICLES.map((v) => <option key={v}>{v}</option>)}
              </select>
            </label>
            {privateCar && (
              <label className="field field-check">
                <span className="field-label">자가용 사전 승인</span>
                <span className="check-inline">
                  <input type="checkbox" checked={form.private_car_approved} onChange={(e) => edit('private_car_approved', e.target.checked)} />
                  자가용 사용을 미리 승인받았어요
                </span>
              </label>
            )}
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="card wiz-card">
          <h2>이대로 신청할까요?</h2>
          <dl className="cal-summary trip-summary">
            <div><dt>구분</dt><dd>{form.trip_type}{!intra && form.education ? ' · 교육 출장' : ''}{intra && form.hours !== '' ? ` · 약 ${form.hours}시간` : ''}</dd></div>
            <div><dt>목적</dt><dd>{form.purpose}</dd></div>
            <div><dt>기간</dt><dd>{periodText(form.start_date, form.end_date)}</dd></div>
            <div><dt>출장지</dt><dd>{form.destination}</dd></div>
            <div>
              <dt>교통</dt>
              <dd>
                {form.vehicle}
                {form.distance_km !== '' ? ` · 편도 약 ${form.distance_km} km` : ''}
                {privateCar ? (form.private_car_approved ? ' · 사전 승인' : ' · 승인 전') : ''}
              </dd>
            </div>
          </dl>
          <p className="hint">실제 결재는 이 화면에서 진행하지 않아요. 신청하면 홈의 ‘내 출장’에 바로 올라가요.</p>
        </div>
      )}

      {error && <div className="error" role="alert">{error}</div>}
      <div className="wiz-nav">
        {step > 1 ? <button type="button" className="btn" onClick={() => go(step - 1)}>이전</button> : <span />}
        {step < 4
          ? <button type="button" className="btn primary" onClick={next}>다음</button>
          : <button type="button" className="btn primary" onClick={submit} disabled={saving}>{saving ? '신청 중…' : '신청하기'}</button>}
      </div>
    </section>
  )
}
