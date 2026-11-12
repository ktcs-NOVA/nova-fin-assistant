// 출발일·도착일을 달력에서 눌러 고르는 부품. 값은 'YYYY-MM-DD' 문자열 (<input type="date"> 와 같은 모양).
// 첫 클릭 = 출발일, 두 번째 클릭 = 도착일 (출발일보다 앞이면 새 출발일). 채은 님 달력 컴포넌트가 정해지면
// 같은 props(start, end, onChange)만 맞춰서 이 파일을 바꾸면 됩니다.

import { useState } from 'react'

const DOW = ['일', '월', '화', '수', '목', '금', '토']
const pad = (n) => String(n).padStart(2, '0')
const iso = (y, m, d) => `${y}-${pad(m + 1)}-${pad(d)}`
const parse = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d) }
const label = (s) => { const d = parse(s); return `${d.getMonth() + 1}월 ${d.getDate()}일 (${DOW[d.getDay()]})` }

/** 출장 기간 문구: 같은 날이면 당일, 아니면 "1박 2일" */
function periodLabel(start, end) {
  if (!start || !end) return ''
  const nights = Math.round((parse(end) - parse(start)) / 86400000)
  return nights <= 0 ? '당일' : `${nights}박 ${nights + 1}일`
}

export default function DateRangePicker({ start, end, onChange }) {
  const [view, setView] = useState(() => {
    const base = start ? parse(start) : new Date()   // 처음 한 번만: 출발일이 있으면 그 달, 없으면 이번 달
    return { y: base.getFullYear(), m: base.getMonth() }
  })

  const first = new Date(view.y, view.m, 1).getDay()
  const days = new Date(view.y, view.m + 1, 0).getDate()
  const cells = [...Array(first).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)]

  function move(delta) {
    const d = new Date(view.y, view.m + delta, 1)
    setView({ y: d.getFullYear(), m: d.getMonth() })
  }

  function pick(day) {
    const v = iso(view.y, view.m, day)
    if (!start || (start && end)) onChange({ start: v, end: '' })
    else if (v < start) onChange({ start: v, end: '' })
    else onChange({ start, end: v })
  }

  return (
    <div className="daterange">
      <div className="cal" role="group" aria-label={`${view.y}년 ${view.m + 1}월 달력`}>
        <div className="cal-head">
          <button type="button" className="btn small" onClick={() => move(-1)} aria-label="이전 달">‹</button>
          <b>{view.y}년 {view.m + 1}월</b>
          <button type="button" className="btn small" onClick={() => move(1)} aria-label="다음 달">›</button>
        </div>
        <div className="cal-grid">
          {DOW.map((d, i) => <span key={d} className={`cal-dow ${i === 0 ? 'sun' : ''}`}>{d}</span>)}
          {cells.map((day, i) => {
            if (!day) return <span key={`e${i}`} />
            const v = iso(view.y, view.m, day)
            const isStart = v === start
            const isEnd = v === end
            const inRange = start && end && v > start && v < end
            return (
              <button
                key={v} type="button"
                className={`cal-day${isStart || isEnd ? ' sel' : ''}${inRange ? ' range' : ''}`}
                aria-pressed={isStart || isEnd}
                aria-label={label(v)}
                onClick={() => pick(day)}
              >{day}</button>
            )
          })}
        </div>
      </div>
      <dl className="cal-summary">
        <div><dt>출발일</dt><dd>{start ? label(start) : '달력에서 고르세요'}</dd></div>
        <div><dt>도착일</dt><dd>{end ? label(end) : start ? '도착일을 고르세요' : '—'}</dd></div>
        <div><dt>기간</dt><dd>{periodLabel(start, end) || '—'}</dd></div>
      </dl>
    </div>
  )
}

