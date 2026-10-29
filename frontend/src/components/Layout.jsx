// 전체 틀: 상단 헤더(로고 + 메뉴 탭) + 본문 영역
// 어떤 화면을 보여줄지는 App.jsx가 정하고, 여기서는 틀만 그립니다.

export default function Layout({ pages, current, onChange, children }) {
  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <span className="logo-mark">經</span>
          <div>
            <div>경비 정산 사전검증</div>
            <div className="logo-sub">한국해양진흥공사 · 팀 NOVA</div>
          </div>
        </div>

        <nav className="nav" aria-label="주요 메뉴">
          {pages.map((p) => (
            <button
              key={p.id}
              className={p.id === current ? 'on' : ''}
              onClick={() => onChange(p.id)}
              aria-current={p.id === current ? 'page' : undefined}
            >
              {p.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="main">{children}</main>
    </div>
  )
}
