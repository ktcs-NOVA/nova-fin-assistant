// 시각 입력 (구글 캘린더 방식): 칸을 누르면 30분 단위 시각 목록이 열리고, 숫자로 바로 쳐도 됩니다.
//   9 · 930 · 0930 · 9:30 · 9시 30분 · 오후 2:30 → 아무 분이나 받음 (여비규정에 분 단위 기준이 없어 목록은 바로가기일 뿐)
// 화면은 '오전 9:30 / 오후 2:30' (12시간제), 값은 'HH:MM' 24시간제 문자열 (<input type="time"> 과 같은 모양). 비우면 ''.
// after: 같은 날 출발 시각 → 복귀 목록에서 그 뒤 시각만 보이고 걸리는 시간 "(4시간 30분)"을 함께 보여 줌

import { useEffect, useRef, useState } from 'react'
import { formatTime, toHHMM, toMin } from '../utils/time.js'

const SLOTS = Array.from({ length: 48 }, (_, i) => i * 30)   // 0:00 ~ 23:30 (분)

function durationText(mins) {
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return [h ? `${h}시간` : '', m ? `${m}분` : ''].filter(Boolean).join(' ')
}

/** 사람이 적은 시각 → 'HH:MM'. 비었으면 '', 알아볼 수 없으면 null */
function parseTime(raw) {
  let t = String(raw ?? '').trim()
  if (!t) return ''
  const half = t.match(/^(오전|오후|am|pm)\s*/i)?.[1]?.toLowerCase()
  if (half) t = t.slice(t.match(/^(오전|오후|am|pm)\s*/i)[0].length)
  let h
  let m
  const korean = t.match(/^(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분?)?$/)
  const colon = t.match(/^(\d{1,2})\s*[:.]\s*(\d{1,2})$/)
  if (korean) { h = Number(korean[1]); m = Number(korean[2] ?? 0) }
  else if (colon) { h = Number(colon[1]); m = Number(colon[2]) }
  else if (/^\d{1,4}$/.test(t)) {
    // 1~2자리: 시만 (9 → 9:00) · 3~4자리: 930 → 9:30, 1430 → 14:30
    if (t.length <= 2) { h = Number(t); m = 0 }
    else { h = Number(t.slice(0, -2)); m = Number(t.slice(-2)) }
  } else return null
  if (half) {
    if (h < 1 || h > 12) return null
    h = half === '오후' || half === 'pm' ? (h % 12) + 12 : h % 12
  }
  if (h > 23 || m > 59) return null
  return toHHMM(h * 60 + m)
}

export default function TimeField({ value, onChange, label, after = '', placeholder = '오전 9:00' }) {
  const [text, setText] = useState(formatTime(value))
  const [open, setOpen] = useState(false)
  const [bad, setBad] = useState(false)
  const [active, setActive] = useState(-1)   // 키보드로 고르는 중인 목록 줄
  const listRef = useRef(null)

  const start = toMin(after)
  const slots = start == null ? SLOTS : SLOTS.filter((m) => m > start)
  const current = toMin(value)

  // 목록을 열면 지금 값(없으면 오전 9시, 복귀는 맨 위) 근처로 스크롤
  useEffect(() => {
    if (!open || !listRef.current) return
    const target = current ?? (start == null ? 9 * 60 : null)
    const idx = target == null ? 0 : Math.max(0, slots.findIndex((m) => m >= target))
    listRef.current.children[idx]?.scrollIntoView({ block: 'center' })
  }, [open])   // eslint-disable-line react-hooks/exhaustive-deps

  function choose(m) {
    const v = toHHMM(m)
    setText(formatTime(v))
    setBad(false)
    setOpen(false)
    setActive(-1)
    onChange(v)
  }

  function type(raw) {
    setText(raw)
    setBad(false)
    setOpen(true)
    const v = parseTime(raw)
    if (v !== null) onChange(v)   // 다 적은 순간 값이 반영됨 (적는 중이라 아직 모르면 그대로 둠)
  }

  function done() {
    setOpen(false)
    setActive(-1)
    const v = parseTime(text)
    if (v === null) { setBad(true); onChange(''); return }
    setText(formatTime(v))   // 930 → 오전 9:30 으로 정리해서 보여 줌
  }

  function key(e) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      setOpen(true)
      const next = Math.min(slots.length - 1, Math.max(0, active + (e.key === 'ArrowDown' ? 1 : -1)))
      setActive(next)
      listRef.current?.children[next]?.scrollIntoView({ block: 'nearest' })
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (open && active >= 0) choose(slots[active])
      else e.currentTarget.blur()
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <span className="time-field">
      <input
        type="text"
        value={text}
        maxLength={12}
        placeholder={placeholder}
        aria-label={label}
        aria-invalid={bad || undefined}
        aria-expanded={open}
        role="combobox"
        autoComplete="off"
        onFocus={() => setOpen(true)}
        onClick={() => setOpen(true)}
        onChange={(e) => type(e.target.value)}
        onBlur={done}
        onKeyDown={key}
      />
      {open && slots.length > 0 && (
        // onClick 막기: 이 칸이 <label> 안에 있어서, 목록을 누른 클릭이 label 을 타고 입력칸으로 가 목록이 다시 열림
        <ul className="time-list" ref={listRef} role="listbox" aria-label={`${label} 목록`} onClick={(e) => e.preventDefault()}>
          {slots.map((m, i) => (
            <li
              key={m}
              role="option"
              aria-selected={m === current}
              className={`${m === current ? 'on' : ''}${i === active ? ' active' : ''}`}
              onMouseDown={(e) => { e.preventDefault(); choose(m) }}
            >
              {formatTime(toHHMM(m))}
              {start != null && <span className="time-dur">({durationText(m - start)})</span>}
            </li>
          ))}
        </ul>
      )}
      {bad && <span className="time-bad" role="alert">9:30, 930, 오후 2:30 처럼 적어 주세요</span>}
    </span>
  )
}
