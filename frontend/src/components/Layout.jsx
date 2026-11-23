// 전체 틀: 상단 헤더(별 로고 + 메뉴 + 로그인 사용자) + 현재 위치(빵부스러기) + 본문
// 2026-11-23: 직원 홈 디자인 개선안에 맞춰 헤더에 상단 메뉴(nav)를 넣었습니다. 메뉴 목록은 App.jsx의 MENUS[역할].nav.
// 어떤 화면을 보여줄지는 App.jsx가 정하고, 여기서는 틀만 그립니다.

import { USE_MOCK, API_BASE } from '../api/client.js'
import Icon from './Icons.jsx'
import AskDock from './AskDock.jsx'

export default function Layout({ user, roleLabel, onLogout, onHome, onAsk, crumbs, nav = [], navCurrent, askDock, children }) {
  return (
    <div className="app">
      <header className="header">
        <button type="button" className="logo logo-btn" onClick={onHome} aria-label="홈으로">
          <svg className="logo-star" width="28" height="28" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3 6.1 20.6l1.3-6.6L2.5 9.4l6.6-.8z" fill="#f4c14b" stroke="#1e2250" strokeWidth="1.6" strokeLinejoin="round" />
          </svg>
          <span>
            <span className="logo-name brand-font">NOVA</span>
          </span>
        </button>

        {nav.length > 0 && (
          <nav className="header-nav" aria-label="주 메뉴">
            {nav.map((n) => (
              <button key={n.id} type="button" onClick={n.go} aria-current={n.id === navCurrent ? 'page' : undefined}>{n.label}</button>
            ))}
          </nav>
        )}

        {/* 지금 목업인지 실제 백엔드인지 한눈에 보이게 */}
        <span className={`mode ${USE_MOCK ? 'mock' : 'live'}`} title={USE_MOCK ? '가짜 응답으로 동작 중' : API_BASE}>
          {USE_MOCK ? '목업 모드' : '백엔드 연결'}
        </span>

        <div className="header-right">
          {nav.length === 0 && <button type="button" className="header-link" onClick={onAsk}>규정 확인하기</button>}

          {/* 로그인한 계정. 역할은 로그인에서 정해지며 여기서 바꿀 수 없음 */}
          <div className="user-chip" title={`${user.department} · ${user.employee_no}`}>
            <span className={`user-role ${user.role}`}>{roleLabel}</span>
            <span className="user-name">{user.name}</span>
            <button type="button" className="user-logout" onClick={onLogout}>로그아웃</button>
          </div>
        </div>
      </header>

      <main className={`main ${askDock ? 'has-dock' : ''}`}>
        {crumbs.length > 1 && (
          <nav className="crumbs" aria-label="현재 위치">
            <button type="button" className="crumb-back" onClick={crumbs[crumbs.length - 2].go}>
              <Icon name="back" size={16} />뒤로
            </button>
            {crumbs.map((c, i) => (
              <span key={c.id}>
                {i > 0 && <span className="crumb-sep" aria-hidden="true">›</span>}
                {i < crumbs.length - 1
                  ? <button type="button" onClick={c.go}>{c.label}</button>
                  : <span aria-current="page">{c.label}</span>}
              </span>
            ))}
          </nav>
        )}
        {children}
      </main>
      {askDock && <AskDock page={askDock} />}
    </div>
  )
}
