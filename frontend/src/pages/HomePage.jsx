// 직원 홈 (2026-11-23 디자인 개선안): 스크롤 없이 한 화면에 다 보이게.
// 왼쪽: 정산하기(크게, 유형 3개 바로 고르기) / 오른쪽: 내 출장(최근 2건 + 출장 신청) · 내 정산 현황 · 문서 작업 / 아래: 규정 확인하기.
// 내 제출 내역(listMySubmissions)·서류(listDocuments)·출장(listTrips)으로 건수를 채웁니다. 목업 모드에서는 예시 데이터예요.

import { useEffect, useState } from 'react'
import { cancelTrip, listDocuments, listMySubmissions, listTrips, VERDICT, STATUS } from '../api/client.js'
import { CLAIM } from '../utils/claimTypes.js'
import { periodText, settleable, STAGE_TONE } from '../utils/trips.js'
import Icon from '../components/Icons.jsx'
import seeker from '../assets/nova-seeker.png'

// 정산 유형: 고르면 유형 선택 화면을 거치지 않고 바로 해당 화면으로 (유형 정의는 TypePage와 같음)
const START = [
  { id: 'trip', title: '국내출장', desc: '신청한 출장을 불러와 규정대로 계산해요', go: 'travel' },
  { id: 'meeting', title: '회의비', desc: '회의 목적과 참석자를 함께 확인해요', go: 'receipt', param: { claim: CLAIM.MEETING } },
  { id: 'card', title: '기타 법인카드 사용', desc: '그 밖의 사용 내역을 사유와 함께 확인해요', go: 'receipt', param: { claim: CLAIM.CARD } },
]

// 자주 묻는 질문 칩: 한 화면에 들어가도록 3개만
const ASK_CHIPS = [
  '숙박비 상한은 얼마인가요?',
  '회의비에 참석자를 꼭 적어야 하나요?',
  '자가용 출장 연료비는 어떻게 계산하나요?',
]

const TRIPS_ON_HOME = 2   // 홈에는 최근 2건만, 나머지는 출장 신청 화면에서

export default function HomePage({ user, onNavigate }) {
  const [rows, setRows] = useState(null)   // null = 불러오는 중
  const [workingDocs, setWorkingDocs] = useState(null)   // 작성 중인 서류 수
  const [question, setQuestion] = useState('')   // 규정 검색바
  const [trips, setTrips] = useState(null)       // 내 출장 (null = 불러오는 중)
  const [tripError, setTripError] = useState('')

  // 질문을 들고 규정 확인하기로: QaPage 가 param.ask 를 받아 바로 물어봅니다.
  function ask(text) {
    const q = text.trim()
    if (q) onNavigate('qa', { ask: q })
  }

  useEffect(() => {
    let ignore = false
    listMySubmissions()
      .then((d) => { if (!ignore) setRows(d.items ?? []) })
      .catch(() => { if (!ignore) setRows([]) })
    return () => { ignore = true }
  }, [])

  useEffect(() => {
    let ignore = false
    listDocuments()
      .then((d) => { if (!ignore) setWorkingDocs(d.filter((x) => x.status !== '작성 완료').length) })
      .catch(() => { if (!ignore) setWorkingDocs(0) })
    return () => { ignore = true }
  }, [])

  useEffect(() => {
    let ignore = false
    listTrips()
      .then((d) => { if (!ignore) setTrips(d) })
      .catch(() => { if (!ignore) setTrips([]) })
    return () => { ignore = true }
  }, [])

  async function cancel(trip) {
    if (!window.confirm(`'${trip.purpose}' 출장 신청을 취소할까요?`)) return
    setTripError('')
    try {
      await cancelTrip(trip.id)
      setTrips((list) => list.filter((t) => t.id !== trip.id))
    } catch (e) {
      setTripError(e.message)
    }
  }

  // 출장 줄 오른쪽 버튼: 지금 단계에서 할 일
  function tripAction(t) {
    if (settleable(t)) return <button type="button" className="btn primary" onClick={() => onNavigate('travel', { tripId: t.id })}>정산하기</button>
    if (t.submission) {
      const rejected = t.submission.status === STATUS.REJECTED   // 반려되면 서류보다 고쳐서 다시 내는 게 먼저
      return <button type="button" className={rejected ? 'btn primary' : 'btn'} onClick={() => onNavigate('mystatus')}>{rejected ? '다시 내기' : '서류 쓰기'}</button>
    }
    return <button type="button" className="link-btn" onClick={() => cancel(t)}>신청 취소</button>
  }

  const mine = rows ?? []
  const count = (n) => (rows === null ? '–' : n)
  const fixCount = mine.filter((s) => s.verdict === VERDICT.FIX).length
  const pendingCount = mine.filter((s) => s.status === STATUS.PENDING).length
  const approvedCount = mine.filter((s) => s.status === STATUS.APPROVED).length

  return (
    <div className="home home-v2">
      <div className="home-v2-head">
        <h1>{user.name} 님, 무엇을 하시겠어요?</h1>
        <p className="hint">하나를 고르면 다음 단계로 안내해 드려요.</p>
      </div>

      <div className="home-v2-grid">
        <section className="home-start" aria-labelledby="home-start-title">
          <h2 id="home-start-title">정산하기</h2>
          <p>무엇을 정산하나요? 고르면 제출하기 전에 규정에 맞는지 확인하고, 서류까지 준비해 드려요.</p>
          <div className="home-start-list">
            {START.map((t) => (
              <button key={t.id} type="button" className="home-start-item" onClick={() => onNavigate(t.go, t.param ?? null)}>
                <span className="home-start-text"><b>{t.title}</b><span>{t.desc}</span></span>
                <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </button>
            ))}
          </div>
        </section>

        <div className="home-side">
          <section className="home-card home-trips-card" aria-labelledby="home-trips-title">
            <div className="home-card-head">
              <h2 id="home-trips-title">내 출장</h2>
              <button type="button" className="home-pill" onClick={() => onNavigate('trip')}>출장 신청</button>
            </div>
            {tripError && <div className="error" role="alert">{tripError}</div>}
            {trips === null && <p>불러오는 중…</p>}
            {trips?.length === 0 && <p>아직 신청한 출장이 없어요. 출장 전에 신청해 두면 정산과 출장보고서에 그대로 이어져요.</p>}
            {trips?.length > 0 && (
              <ul className="home-trip-list">
                {trips.slice(0, TRIPS_ON_HOME).map((t) => (
                  <li key={t.id}>
                    <button type="button" className="home-trip-main" onClick={() => onNavigate('trip', { tripId: t.id })} title="신청 내역 보기">
                      <b>{t.purpose}</b>
                      <span>{periodText(t.start_date, t.end_date)} · {t.destination || t.region || '출장지 미정'}</span>
                    </button>
                    <span className={`badge ${STAGE_TONE[t.stage] ?? 'muted'}`}>{t.stage}</span>
                    {tripAction(t)}
                  </li>
                ))}
              </ul>
            )}
            {trips?.length > TRIPS_ON_HOME && (
              <button type="button" className="home-card-go" onClick={() => onNavigate('trip')}>전체 보기 ({trips.length}건)</button>
            )}
          </section>

          <div className="home-mini-row">
            <section className="home-card home-mini" aria-labelledby="home-status-title">
              <h2 id="home-status-title">내 정산 현황</h2>
              <p>검토 대기 <b>{count(pendingCount)}</b> · 승인 <b className="ok">{count(approvedCount)}</b></p>
              {fixCount > 0 ? (
                <button type="button" className="home-fix" onClick={() => onNavigate('mystatus')}>
                  <span className="stamp-s fix">보완 필요</span>
                  <span>{fixCount}건</span>
                </button>
              ) : (
                <button type="button" className="home-card-go" onClick={() => onNavigate('mystatus')}>전체 보기</button>
              )}
            </section>

            <section className="home-card home-mini" aria-labelledby="home-docs-title">
              <h2 id="home-docs-title">문서 작업</h2>
              <p>{workingDocs ? `작성 중인 서류 ${workingDocs}건` : '정산한 건의 서류를 써요'}</p>
              <button type="button" className="home-card-go" onClick={() => onNavigate('checklist')}>{workingDocs ? '이어서 쓰기' : '열기'}</button>
            </section>
          </div>
        </div>
      </div>

      <section className="home-ask" aria-labelledby="home-ask-title">
        <img className="home-ask-mascot" src={seeker} alt="" width="96" height="92" />
        <div className="home-ask-body">
          <div className="home-ask-head">
            <h2 id="home-ask-title">규정 확인하기</h2>
            <span className="hint">근거 조항과 함께 답해 드려요. 근거가 없으면 지어내지 않고 담당자 확인으로 안내해요.</span>
          </div>
          <form className="ask-bar" onSubmit={(e) => { e.preventDefault(); ask(question) }}>
            <Icon name="search" size={22} />
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="규정을 물어보세요!  예) 부산 1박 출장 숙박비 상한은?"
              maxLength={1000}
              aria-label="규정 질문"
            />
            <button type="submit" className="btn primary" disabled={!question.trim()}>질문하기</button>
          </form>
          <div className="chips" aria-label="자주 묻는 질문">
            {ASK_CHIPS.map((q) => (
              <button key={q} type="button" className="chip" onClick={() => ask(q)}>{q}</button>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
