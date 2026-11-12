// 전체 틀: 상단 헤더(로고 + 규정 물어보기 + 로그인 사용자) + 현재 위치(빵부스러기) + 본문
// 어떤 화면을 보여줄지는 App.jsx가 정하고, 여기서는 틀만 그립니다.

import { USE_MOCK, API_BASE } from '../api/client.js'

export default function Layout({ user, roleLabel, onLogout, onHome, onAsk, crumbs, children }) {
  return (
    <div className="app">
      <header className="header">
        <button type="button" className="logo logo-btn" onClick={onHome} aria-label="홈으로">
          <span className="logo-mark">經</span>
          <span>
            <span className="logo-name">경비 정산 사전검증</span>
            <span className="logo-sub">한국해양진흥공사 · 팀 NOVA</span>
          </span>
        </button>

        {/* 지금 목업인지 실제 백엔드인지 한눈에 보이게 */}
        <span className={`mode ${USE_MOCK ? 'mock' : 'live'}`} title={USE_MOCK ? '가짜 응답으로 동작 중' : API_BASE}>
          {USE_MOCK ? '목업 모드' : '백엔드 연결'}
        </span>

        <div className="header-right">
          <button type="button" className="header-link" onClick={onAsk}>규정 물어보기</button>

          {/* 로그인한 계정. 역할은 로그인에서 정해지며 여기서 바꿀 수 없음 */}
          <div className="user-chip" title={`${user.department} · ${user.employee_no}`}>
            <span className={`user-role ${user.role}`}>{roleLabel}</span>
            <span className="user-name">{user.name}</span>
            <button type="button" className="user-logout" onClick={onLogout}>로그아웃</button>
          </div>
        </div>
      </header>

      <main className="main">
        {crumbs.length > 1 && (
          <nav className="crumbs" aria-label="현재 위치">
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
    </div>
  )
}
