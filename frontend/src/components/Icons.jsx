// 화면 곳곳에서 쓰는 작은 아이콘 모음. 선 아이콘(stroke)이라 글자색(currentColor)을 따라갑니다.
// path 는 24x24 기준. 아이콘을 더 쓰고 싶으면 ICONS 에 한 줄 추가하세요.

const ICONS = {
  logo: <><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v4h4M9.5 14l2 2 3.5-4" /></>,
  camera: <><path d="M4 8h3l1.5-2h7L17 8h3v11H4z" /><circle cx="12" cy="13" r="3.5" /></>,
  upload: <path d="M12 16V4M7 9l5-5 5 5M5 20h14" />,
  eye: <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></>,
  eyeOff: <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /><path d="M4 4l16 16" /></>,
  back: <path d="M15 5l-7 7 7 7" />,
  warn: <><path d="M12 3.5 2.5 20h19z" /><path d="M12 10v4.5M12 17.5h.01" /></>,
  trip: <><rect x="6" y="3" width="12" height="14" rx="3" /><path d="M6 11h12M9 14h.01M15 14h.01M9 17l-2 4M15 17l2 4" /></>,
  meal: <path d="M7 3v8M5 3v5a2 2 0 0 0 4 0V3M7 11v10M17 3c-2 2-3 5-3 8h3v10" />,
  meeting: <><circle cx="9" cy="9" r="3" /><circle cx="17" cy="10" r="2.5" /><path d="M3 19c.6-3 3-4.5 6-4.5s5.4 1.5 6 4.5M15.5 14.7c3 0 4.8 1.3 5.5 4" /></>,
  card: <><rect x="3" y="6" width="18" height="12" rx="2" /><path d="M3 10h18M7 15h4" /></>,
}

export default function Icon({ name, size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flex: 'none' }}>
      {ICONS[name]}
    </svg>
  )
}
