// 로그인 / 회원가입 화면 (좌: 서비스 소개 / 우: 폼). 사번(또는 이메일)+비밀번호로 POST /api/auth/login, 가입은 POST /api/auth/signup (항상 직원 계정).
// 직원인지 관리자인지는 계정이 정합니다. 아래 '시연 계정'을 누르면 바로 로그인합니다(VITE_SHOW_DEMO=false 면 숨김). 시연 계정·공통 비밀번호는 auth/accounts.js.

import { useState } from 'react'
import { DEMO_ACCOUNTS, DEMO_PASSWORD, GRADES, ROLE_LABEL } from '../auth/accounts.js'
import { login, signup, USE_MOCK, API_BASE } from '../api/client.js'
import mascot from '../assets/nova-mascot.png'
import PasswordField from '../components/PasswordField.jsx'
import EmailField from '../components/EmailField.jsx'

const EMPTY_SIGNUP = { name: '', employeeNo: '', department: '', grade: GRADES[0], email: '', password: '' }

const SHOW_DEMO = import.meta.env.VITE_SHOW_DEMO !== 'false'

export default function LoginPage({ onLogin }) {
  const [mode, setMode] = useState('login')            // 'login' | 'signup' (가입은 항상 직원 계정)
  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [form, setForm] = useState(EMPTY_SIGNUP)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const signupMode = mode === 'signup'
  const setField = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

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
    if (missing) { setError(missing === 'email' ? '이메일 아이디와 도메인을 모두 입력해 주세요.' : '모든 칸을 채워 주세요.'); return }
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

  // 시연 계정: 누르면 바로 로그인
  async function demoLogin(a) {
    setLoading(true); setError('')
    try {
      onLogin(await login(a.employee_no, DEMO_PASSWORD))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-split">
      <section className="login-hero" aria-label="서비스 소개">
        <div className="login-brand">
          <img className="login-mascot" src={mascot} alt="NOVA 마스코트" width="360" height="272" />
          <span className="login-wordmark" aria-label="NOVA">
            {'NOVA'.split('').map((ch, i) => (
              <span key={i} className="reveal-ch" style={{ '--i': i }} aria-hidden="true">{ch}</span>
            ))}
          </span>
        </div>
        <p className="login-lead">
          <span className="reveal-line" style={{ '--d': '2.3s' }}>제출하기 전에,</span>
          <span className="reveal-line" style={{ '--d': '3s' }}>규정에 맞는지 먼저 확인하세요</span>
        </p>
        <p className="login-sub">출장비 계산부터 규정 검증, 증빙 서류까지 한 곳에서. 판정마다 근거 조항을 함께 보여 드려요.</p>
      </section>

      <section className="login-pane">
        <div className="login-panel">
          <div className="login-top">
            <span className={`mode ${USE_MOCK ? 'mock' : 'live'}`} title={USE_MOCK ? '가짜 응답으로 동작 중' : API_BASE}>
              {USE_MOCK ? '목업 모드' : '백엔드 연결'}
            </span>
          </div>

          <div className="login-head">
            <h2>{signupMode ? '처음이신가요?' : '로그인'}</h2>
            <p className="hint">
              {signupMode ? '직급은 규정 판정(숙박비·교통 등급 등)에 사용돼요.' : '사번 또는 이메일로 로그인하세요.'}
            </p>
          </div>

          {error && <div className="error" role="alert">{error}</div>}

          {signupMode ? (
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
                <label className="field field-wide">
                  <span className="field-label">이메일</span>
                  <EmailField onChange={(email) => setForm((f) => ({ ...f, email }))} />
                </label>
                <label className="field">
                  <span className="field-label">비밀번호 <em>4자 이상</em></span>
                  <PasswordField value={form.password} onChange={setField('password')} autoComplete="new-password" />
                </label>
              </div>
              <button className="btn primary login-submit" type="submit" disabled={loading}>{loading ? '만드는 중…' : '가입하고 시작하기'}</button>
              <p className="hint">가입하면 직원 계정으로 만들어져요. 비밀번호는 암호화해서 저장해요.</p>
              <p className="hint center">이미 계정이 있으신가요? <button type="button" className="link-btn" onClick={() => { setMode('login'); setError('') }}>로그인</button></p>
            </form>
          ) : (
            <form className="login-form" onSubmit={submitLogin}>
              <label className="field">
                <span className="field-label">사번 또는 이메일</span>
                <input type="text" value={loginId} onChange={(e) => setLoginId(e.target.value)} autoComplete="username" placeholder="예) E1001" />
              </label>
              <label className="field">
                <span className="field-label">비밀번호</span>
                <PasswordField value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" placeholder="비밀번호를 입력하세요" />
              </label>
              <button className="btn primary login-submit" type="submit" disabled={loading}>{loading ? '확인 중…' : '로그인'}</button>
              <p className="hint center">계정이 없으신가요? <button type="button" className="link-btn" onClick={() => { setMode('signup'); setError('') }}>회원가입</button></p>
            </form>
          )}

          {SHOW_DEMO && !signupMode && (
            <section className="login-demo">
              <h2>시연 계정으로 바로 둘러보기</h2>
              <div className="login-accounts">
                {DEMO_ACCOUNTS.map((a) => (
                  <button key={a.employee_no} type="button" className={`login-account ${a.role}`} onClick={() => demoLogin(a)} disabled={loading}>
                    <span className="login-avatar">{a.name.slice(0, 1)}</span>
                    <span className="login-name">{a.name}</span>
                    <span className="login-meta">{ROLE_LABEL[a.role]} · {a.department}</span>
                  </button>
                ))}
              </div>
            </section>
          )}
        </div>
      </section>
    </div>
  )
}
