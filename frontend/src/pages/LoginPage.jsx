// 시연용 로그인: 팀원 이름을 고르면 역할(직원 / 회계 관리자)에 맞는 화면으로 들어갑니다.
// 비밀번호 없음. 계정 목록은 auth/accounts.js (백엔드 시드와 동일).

import { ACCOUNTS, ROLE, ROLE_LABEL } from '../auth/accounts.js'
import { USE_MOCK, API_BASE } from '../api/client.js'

export default function LoginPage({ onLogin }) {
  const groups = [ROLE.EMPLOYEE, ROLE.ADMIN].map((role) => ({
    role,
    label: ROLE_LABEL[role],
    accounts: ACCOUNTS.filter((a) => a.role === role),
  }))

  return (
    <div className="login-page">
      <div className="login-box">
        <div className="login-brand">
          <span className="logo-mark">經</span>
          <div>
            <h1>경비 정산 사전검증</h1>
            <p className="logo-sub">한국해양진흥공사 · 팀 NOVA</p>
          </div>
          <span className={`mode ${USE_MOCK ? 'mock' : 'live'}`} title={USE_MOCK ? '가짜 응답으로 동작 중' : API_BASE}>
            {USE_MOCK ? '목업 모드' : '백엔드 연결'}
          </span>
        </div>

        <p className="login-hint">계정을 선택하면 역할에 맞는 화면으로 들어갑니다. (시연용 · 비밀번호 없음)</p>

        {groups.map((g) => (
          <section key={g.role} className="login-group">
            <h2>{g.label}</h2>
            <div className="login-accounts">
              {g.accounts.map((a) => (
                <button key={a.employee_no} type="button" className={`login-account ${g.role}`} onClick={() => onLogin(a)}>
                  <span className="login-avatar">{a.name.slice(0, 1)}</span>
                  <span className="login-name">{a.name}</span>
                  <span className="login-meta">{a.department} · {a.employee_no}</span>
                  <span className="login-enter">{g.role === ROLE.ADMIN ? '관리자 화면으로 →' : '직원 화면으로 →'}</span>
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
