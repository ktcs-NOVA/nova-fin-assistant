// 시연용 로그인: 직원 / 관리자 탭을 고르고 사번을 입력(또는 아래 계정 버튼)하면 들어갑니다.
// 비밀번호·회원가입은 백엔드 인증이 생기면 붙입니다. 지금은 사번을 X-Employee-No 헤더로 보내는 방식(auth/accounts.js).

import { useState } from 'react'
import { ACCOUNTS, ROLE } from '../auth/accounts.js'
import { USE_MOCK, API_BASE } from '../api/client.js'

const TABS = [
  { role: ROLE.EMPLOYEE, label: '직원', title: '다시 오셨네요', desc: '사번을 입력하거나 아래 계정을 고르세요.', placeholder: '예) E1001' },
  { role: ROLE.ADMIN, label: '관리자', title: '관리자 로그인', desc: '검토 대기함과 승인·반려를 관리해요.', placeholder: '예) A2001' },
]

const POINTS = [
  '영수증을 찍으면 금액·날짜를 자동으로 읽어요',
  '필요한 서류를 하나씩 따라가며 채워요',
  '판정 결과에는 근거 조항이 함께 나와요',
]

export default function LoginPage({ onLogin }) {
  const [role, setRole] = useState(ROLE.EMPLOYEE)
  const [empNo, setEmpNo] = useState('')
  const [error, setError] = useState('')

  const tab = TABS.find((t) => t.role === role)
  const accounts = ACCOUNTS.filter((a) => a.role === role)

  function submit(e) {
    e.preventDefault()
    const found = accounts.find((a) => a.employee_no.toLowerCase() === empNo.trim().toLowerCase())
    if (!found) {
      setError(`${tab.label} 계정에 없는 사번이에요. 아래 계정에서 골라 주세요.`)
      return
    }
    onLogin(found)
  }

  return (
    <div className="login-split">
      <section className="login-hero" aria-label="서비스 소개">
        <h1>제출하기 전에,<br />규정에 맞는지 먼저 확인하세요</h1>
        <p>한국해양진흥공사 여비규정을 근거로<br />출장비 정산 서류를 미리 점검해 드려요.</p>
        <ul>
          {POINTS.map((t) => (<li key={t}><span className="check" aria-hidden="true">✓</span>{t}</li>))}
        </ul>
      </section>

      <section className="login-pane">
        <div className="login-form">
          <div className="login-top">
            <span className="logo-mark">經</span>
            <span className={`mode ${USE_MOCK ? 'mock' : 'live'}`} title={USE_MOCK ? '가짜 응답으로 동작 중' : API_BASE}>
              {USE_MOCK ? '목업 모드' : '백엔드 연결'}
            </span>
          </div>

          <div>
            <div className="login-q">어떤 계정으로 들어가시나요?</div>
            <div className="seg" role="tablist">
              {TABS.map((t) => (
                <button
                  key={t.role} type="button" role="tab" aria-selected={role === t.role}
                  className={role === t.role ? 'on' : ''}
                  onClick={() => { setRole(t.role); setEmpNo(''); setError('') }}
                >{t.label}</button>
              ))}
            </div>
          </div>

          <form onSubmit={submit} className="login-fields">
            <div>
              <h2>{tab.title}</h2>
              <p className="hint">{tab.desc}</p>
            </div>
            <label htmlFor="login-empno">사번</label>
            <input
              id="login-empno" className="input" type="text" autoComplete="username"
              value={empNo} placeholder={tab.placeholder}
              onChange={(e) => { setEmpNo(e.target.value); setError('') }}
            />
            {error && <p className="login-error" role="alert">{error}</p>}
            <button type="submit" className="btn primary block">{role === ROLE.ADMIN ? '관리자로 로그인' : '로그인'}</button>
          </form>

          <div>
            <div className="login-pick-label">시연용 계정 (누르면 바로 들어가요)</div>
            <div className="login-accounts">
              {accounts.map((a) => (
                <button key={a.employee_no} type="button" className={`login-account ${role}`} onClick={() => onLogin(a)}>
                  <span className="login-avatar">{a.name.slice(0, 1)}</span>
                  <span className="login-name">{a.name}</span>
                  <span className="login-meta">{a.department} · {a.employee_no}</span>
                </button>
              ))}
            </div>
            <p className="hint">시연용이라 비밀번호는 없어요. 회원가입은 로그인 인증이 연결된 뒤에 열려요.</p>
          </div>
        </div>
      </section>
    </div>
  )
}
