// 로그인 / 회원가입 화면 (좌: 서비스 소개 / 우: 폼). 위쪽 직원·관리자 탭으로 들어갈 계정 종류를 고릅니다.
// 사번(또는 이메일)+비밀번호로 POST /api/auth/login, 가입은 POST /api/auth/signup (항상 직원 계정).
// 탭과 계정의 실제 역할이 다르면 들어가지 않고 탭을 바꾸라고 안내합니다. 시연 계정·공통 비밀번호는 auth/accounts.js.

import { useState } from 'react'
import { DEMO_ACCOUNTS, DEMO_PASSWORD, GRADES, ROLE, ROLE_LABEL } from '../auth/accounts.js'
import { login, signup, USE_MOCK, API_BASE } from '../api/client.js'
import Icon from '../components/Icons.jsx'
import PasswordField from '../components/PasswordField.jsx'
import EmailField from '../components/EmailField.jsx'

const EMPTY_SIGNUP = { name: '', employeeNo: '', department: '', grade: GRADES[0], email: '', password: '' }

const TABS = [
  { role: ROLE.EMPLOYEE, label: '직원' },
  { role: ROLE.ADMIN, label: '관리자' },
]

const POINTS = [
  '영수증을 찍으면 금액·날짜를 자동으로 읽어요',
  '필요한 서류를 하나씩 따라가며 채워요',
  '판정 결과에는 근거 조항이 함께 나와요',
]

export default function LoginPage({ onLogin }) {
  const [role, setRole] = useState(ROLE.EMPLOYEE)
  const [mode, setMode] = useState('login')            // 'login' | 'signup' (가입은 직원 탭에서만)
  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [form, setForm] = useState(EMPTY_SIGNUP)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const isAdmin = role === ROLE.ADMIN
  const signupMode = !isAdmin && mode === 'signup'
  const demos = DEMO_ACCOUNTS.filter((a) => a.role === role)
  const setField = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  function pickRole(next) {
    setRole(next); setMode('login'); setError(''); setLoginId(''); setPassword('')
  }

  // 응답 계정의 역할이 고른 탭과 같을 때만 들어감
  function enter(session) {
    if (session.user.role !== role) {
      setError(session.user.role === ROLE.ADMIN
        ? '관리자 계정이에요. 위에서 “관리자” 탭을 선택해 주세요.'
        : '직원 계정이에요. 위에서 “직원” 탭을 선택해 주세요.')
      return
    }
    onLogin(session)
  }

  async function submitLogin(e) {
    e.preventDefault()
    if (!loginId.trim() || !password) { setError('사번(또는 이메일)과 비밀번호를 입력해 주세요.'); return }
    setLoading(true); setError('')
    try {
      enter(await login(loginId.trim(), password))
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

  function fillDemo(a) {
    setLoginId(a.employee_no); setPassword(DEMO_PASSWORD); setError('')
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
        <div className="login-panel">
          <div className="login-top">
            <span className="logo-mark"><Icon name="logo" size={20} /></span>
            <span className={`mode ${USE_MOCK ? 'mock' : 'live'}`} title={USE_MOCK ? '가짜 응답으로 동작 중' : API_BASE}>
              {USE_MOCK ? '목업 모드' : '백엔드 연결'}
            </span>
          </div>

          <div>
            <div className="login-q">어떤 계정으로 들어가시나요?</div>
            <div className="seg" role="tablist">
              {TABS.map((t) => (
                <button key={t.role} type="button" role="tab" aria-selected={role === t.role} className={role === t.role ? 'on' : ''} onClick={() => pickRole(t.role)}>{t.label}</button>
              ))}
            </div>
          </div>

          <div className="login-head">
            <h2>{isAdmin ? '관리자 로그인' : signupMode ? '처음이신가요?' : '다시 오셨네요'}</h2>
            <p className="hint">
              {isAdmin ? '검토 대기함과 승인·반려를 관리해요.'
                : signupMode ? '직급은 규정 판정(숙박비·교통 등급 등)에 사용돼요.'
                : '사번 또는 이메일로 로그인하세요.'}
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
                <input type="text" value={loginId} onChange={(e) => setLoginId(e.target.value)} autoComplete="username" placeholder={isAdmin ? '예) A2001' : '예) E1001'} />
              </label>
              <label className="field">
                <span className="field-label">비밀번호</span>
                <PasswordField value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" placeholder="비밀번호를 입력하세요" />
              </label>
              <button className="btn primary login-submit" type="submit" disabled={loading}>{loading ? '확인 중…' : isAdmin ? '관리자로 로그인' : '로그인'}</button>
              {isAdmin
                ? <p className="hint center">관리자 계정은 담당자가 따로 만들어 드려요. 회원가입은 직원만 할 수 있어요.</p>
                : <p className="hint center">계정이 없으신가요? <button type="button" className="link-btn" onClick={() => { setMode('signup'); setError('') }}>회원가입</button></p>}
            </form>
          )}

          {!signupMode && (
            <section className="login-demo">
              <h2>시연 계정 <span className="hint">(비밀번호 공통 {DEMO_PASSWORD} · 누르면 채워집니다)</span></h2>
              <div className="login-accounts">
                {demos.map((a) => (
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
      </section>
    </div>
  )
}
