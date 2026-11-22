// 직원 홈: "무엇을 하시겠어요?" 큰 타일 4개 + 내 출장 + 규정 검색바.
// 2026-11-23: 출장 신청 타일과 '내 출장'(신청한 출장의 진행 단계 · 다음에 할 일 버튼)을 추가했습니다.
// 내 제출 내역(listMySubmissions)으로 보완 알림과 건수를 채웁니다. 목업 모드에서는 예시 데이터예요.

import { useEffect, useState } from 'react'
import { cancelTrip, listDocuments, listMySubmissions, listTrips, VERDICT } from '../api/client.js'
import Icon from '../components/Icons.jsx'
import { periodText, settleable, STAGE_TONE } from '../utils/trips.js'

// 자주 묻는 질문 칩 (2026-11-15: 홈 하단에 규정 검색바 — 눌러서 바로 규정 물어보기로)
const ASK_CHIPS = [
  '숙박비 상한은 얼마인가요?',
  '철도·버스 증빙이 없을 때는 어떻게 하나요?',
  '회의비에 참석자를 꼭 적어야 하나요?',
  '자가용 출장 연료비는 어떻게 계산하나요?',
]

export default function HomePage({ user, onNavigate }) {
  const [rows, setRows] = useState(null)   // null = 불러오는 중
  const [workingDocs, setWorkingDocs] = useState(null)   // 작성 중인 서류 수
  const [question, setQuestion] = useState('')   // 하단 규정 검색바
  const [trips, setTrips] = useState(null)       // 내 출장 (null = 불러오는 중)
  const [tripError, setTripError] = useState('')

  // 질문을 들고 규정 물어보기로: QaPage 가 param.ask 를 받아 바로 물어봅니다.
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

  // 출장 카드 오른쪽 버튼: 지금 단계에서 할 일
  function tripAction(t) {
    if (settleable(t)) return <button type="button" className="btn primary" onClick={() => onNavigate('travel', { tripId: t.id })}>정산하기 →</button>
    if (t.submission) return <button type="button" className="btn" onClick={() => onNavigate('mystatus')}>{t.submission.status} · 서류 쓰기 →</button>
    return <button type="button" className="link-btn" onClick={() => cancel(t)}>신청 취소</button>
  }

  const mine = rows ?? []
  const fixCount = mine.filter((s) => s.verdict === VERDICT.FIX).length
  const pendingCount = mine.filter((s) => s.status === '검토 대기').length

  return (
    <div className="home">
      <h1>{user.name} 님, 무엇을 하시겠어요?</h1>
      <p className="hint">아래에서 하나를 고르면 다음 단계로 안내해 드려요.</p>

      {fixCount > 0 && (
        <button type="button" className="notice-bar" onClick={() => onNavigate('mystatus')}>
          <span><b>보완이 필요한 정산 {fixCount}건</b>이 있어요. 내용을 확인해 주세요.</span>
          <span className="notice-go">확인하기 →</span>
        </button>
      )}

      <div className="tile-grid hero four">
        <button type="button" className="tile" onClick={() => onNavigate('trip')}>
          <span className="tile-title">출장 신청</span>
          <span className="tile-desc">출장 목적·기간·장소를 미리 적어 두면 정산과 출장보고서에 그대로 이어져요.</span>
          <span className="tile-go">신청하기 →</span>
        </button>
        <button type="button" className="tile" onClick={() => onNavigate('type')}>
          <span className="tile-title">정산하기</span>
          <span className="tile-desc">출장, 회의비, 법인카드 사용 내역을 제출하기 전에 규정에 맞는지 확인하고 서류를 준비해요.</span>
          <span className="tile-go">시작하기 →</span>
        </button>
        <button type="button" className="tile" onClick={() => onNavigate('mystatus')}>
          <span className="tile-title">내 정산 현황</span>
          <span className="tile-desc">제출한 정산과 반려·보완 요청을 한눈에 확인해요.</span>
          <span className="tile-go">{rows === null ? '불러오는 중…' : `검토 대기 ${pendingCount}건 · 보완 ${fixCount}건`}</span>
        </button>
        <button type="button" className="tile" onClick={() => onNavigate('checklist')}>
          <span className="tile-title">문서 작업</span>
          <span className="tile-desc">정산한 건의 지출 결과서·회의록·출장보고서를 양식으로 쓰고, 관리자에게 보내요.</span>
          <span className="tile-go">{workingDocs ? `이어서 쓰기 ${workingDocs}건 →` : '열기 →'}</span>
        </button>
      </div>

      <section className="home-trips" aria-labelledby="home-trips-title">
        <div className="home-ask-head">
          <h2 id="home-trips-title">내 출장</h2>
          <span className="hint">신청한 출장의 진행 단계와 다음에 할 일</span>
        </div>
        {tripError && <div className="error" role="alert">{tripError}</div>}
        {trips === null && <div className="empty">불러오는 중…</div>}
        {trips?.length === 0 && (
          <div className="empty">아직 신청한 출장이 없어요. <button type="button" className="link-btn" onClick={() => onNavigate('trip')}>출장 신청하기 →</button></div>
        )}
        {trips?.length > 0 && (
          <ul className="recent-list trip-list">
            {trips.slice(0, 5).map((t) => (
              <li key={t.id}>
                <div className="trip-main">
                  <div className="recent-name">{t.purpose}</div>
                  <div className="hint">{periodText(t.start_date, t.end_date)} · {t.destination || t.region || '출장지 미정'} · {t.vehicle}</div>
                </div>
                <span className="trip-side">
                  <span className={`badge ${STAGE_TONE[t.stage] ?? 'muted'}`}>{t.stage}</span>
                  {tripAction(t)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="home-ask" aria-labelledby="home-ask-title">
        <div className="home-ask-head">
          <h2 id="home-ask-title">규정 물어보기</h2>
          <span className="hint">근거 조항과 함께 알려 드려요</span>
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
        <div className="ask-chips">
          <span className="hint">자주 묻는 질문</span>
          <div className="chips">
            {ASK_CHIPS.map((q) => (
              <button key={q} type="button" className="chip" onClick={() => ask(q)}>{q}</button>
            ))}
          </div>
        </div>
        <p className="hint">근거를 찾을 수 없는 질문은 답을 지어내지 않고 담당자 확인으로 안내해 드려요.</p>
      </section>
    </div>
  )
}
