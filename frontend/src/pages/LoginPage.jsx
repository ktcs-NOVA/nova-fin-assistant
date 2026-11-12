// 로그인 / 회원가입 화면. 사번(또는 이메일)과 비밀번호로 POST /api/auth/login 에 들어가고,
// 응답의 역할(직원 / 회계 관리자)에 맞는 화면으로 들어갑니다. 회원가입은 항상 직원 계정을 만듭니다.
// 시연 계정은 auth/accounts.js (백엔드 시드와 동일) 에 있고 아래 안내에 보여 줍니다.

import { useState } from 'react'
import { DEMO_ACCOUNTS, DEMO_PASSWORD, GRADES, ROLE_LABEL } from '../auth/accounts.js'
import { login, signup, USE_MOCK, API_BASE } from '../api/client.js'

const EMPTY_SIGNUP = { name: '', employeeNo: '', department: '', grade: GRADES[0], email: '', password: '' }

export default function LoginPage({ onLogin }) {
  const [mode, setMode] = useState('login')          // 'login' | 'signup'
  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [form, setForm] = useState(EMPTY_SIGNUP)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function switchMode(next) {
    setMode(next); setError('')
  }

  async function submitLogin(e) {
    e.preventDefault()
    if (!loginId.trim() || !password) { setError('사번(또는 이메일)과 비밀번호를 입력해 주세요.'); return }
    setLoading(true); setError('')
    try {
      onLogin(await login(loginId.trim(), password))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function submitSignup(e) {
    e.preventDefault()
    const missing = ['name', 'employeeNo', 'department', 'email', 'password'].find((k) => !form[k].trim())
    if (missing) { setError('모든 칸을 채워 주세요.'); return }
    if (form.password.length < 4) { setError('비밀번호는 4자 이상이어야 합니다.'); return }
    setLoading(true); setError('')
    try {
      onLogin(await signup(form))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function fillDemo(a) {
    setLoginId(a.employee_no); setPassword(DEMO_PASSWORD); setError('')
  }

  const setField = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

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

        <div className="login-tabs" role="tablist">
          <button type="button" role="tab" aria-selected={mode === 'login'} className={mode === 'login' ? 'on' : ''} onClick={() => switchMode('login')}>로그인</button>
          <button type="button" role="tab" aria-selected={mode === 'signup'} className={mode === 'signup' ? 'on' : ''} onClick={() => switchMode('signup')}>회원가입</button>
        </div>

        {error && <div className="error" role="alert">{error}</div>}

        {mode === 'login' ? (
          <form className="login-form" onSubmit={submitLogin}>
            <label className="field">
              <span className="field-label">사번 또는 이메일</span>
              <input type="text" value={loginId} onChange={(e) => setLoginId(e.target.value)} autoComplete="username" autoFocus placeholder="E1001 또는 e1001@kobc.example" />
            </label>
            <label className="field">
              <span className="field-label">비밀번호</span>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </label>
            <button className="btn primary login-submit" type="submit" disabled={loading}>{loading ? '확인 중…' : '로그인'}</button>
            <p className="hint">역할(직원 / 회계 관리자)은 계정에 정해져 있어 로그인하면 그 화면으로 들어갑니다.</p>
          </form>
        ) : (
          <form className="login-form" onSubmit={submitSignup}>
            <div className="form-grid">
              <label className="field">
                <span className="field-label">이름</span>
                <input type="text" value={form.name} onChange={setField('name')} autoComplete="name" autoFocus />
              </label>
              <label className="field">
                <span className="field-label">사번</span>
                <input type="text" value={form.employeeNo} onChange={setField('employeeNo')} placeholder="예: E1010" />
              </label>
              <label className="field">
                <span className="field-label">부서</span>
                <input type="text" value={form.department} onChange={setField('department')} placeholder="예: 해운정책팀" />
              </label>
              <label className="field">
                <span className="field-label">여비 직급</span>
                <select value={form.grade} onChange={setField('grade')}>
                  {GRADES.map((g) => <option key={g} value={g}>{g}</option>)}
                </select>
              </label>
              <label className="field">
                <span className="field-label">이메일</span>
                <input type="email" value={form.email} onChange={setField('email')} autoComplete="email" />
              </label>
              <label className="field">
                <span className="field-label">비밀번호 <em>4자 이상</em></span>
                <input type="password" value={form.password} onChange={setField('password')} autoComplete="new-password" />
              </label>
            </div>
            <button className="btn primary login-submit" type="submit" disabled={loading}>{loading ? '만드는 중…' : '가입하고 시작하기'}</button>
            <p className="hint">가입하면 바로 직원 화면으로 들어갑니다. 회계 관리자 계정은 가입으로 만들 수 없고 관리부서가 등록합니다.</p>
          </form>
        )}

        {mode === 'login' && (
          <section className="login-demo">
            <h2>시연 계정 <span className="hint">(비밀번호 공통 {DEMO_PASSWORD} · 누르면 채워집니다)</span></h2>
            <div className="login-accounts">
              {DEMO_ACCOUNTS.map((a) => (
                <button key={a.employee_no} type="button" className={`login-account ${a.role}`} onClick={() => fillDemo(a)}>
                  <span className="login-avatar">{a.name.slice(0, 1)}</span>
                  <span className="login-name">{a.name}</span>
                  <span className="login-meta">{ROLE_LABEL[a.role]} · {a.department} · {a.employee_no}</span>
                </button>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
