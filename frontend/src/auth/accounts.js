// 로그인 세션 저장소. 로그인(POST /api/auth/login)·회원가입이 준 { token, user } 를 브라우저에 기억합니다.
// 모든 API 요청은 이 토큰을 Authorization: Bearer 헤더로 보냅니다 (api/client.js). 예전 X-Employee-No 헤더는 없어졌습니다.

export const ROLE = { EMPLOYEE: 'employee', ADMIN: 'admin' }
export const ROLE_LABEL = { employee: '직원', admin: '회계 관리자' }

// 여비 직급 (회원가입 선택지. 백엔드 청구 검증의 grade 값과 같음)
export const GRADES = ['직원 3급 이하', '직원 1·2급', '임원/본부장', '감사', '사장']

// 시연 계정 안내용 목록. 백엔드 scripts/seed.py 의 USERS·DEMO_PASSWORD 와 같아야 합니다.
export const DEMO_PASSWORD = 'nova1234'
export const DEMO_ACCOUNTS = [
  { employee_no: 'E1001', name: '노은비', department: '기획팀', grade: '직원 3급 이하', role: ROLE.EMPLOYEE },
  { employee_no: 'E1002', name: '박철환', department: '총무인사부', grade: '직원 1·2급', role: ROLE.EMPLOYEE },
  { employee_no: 'E1003', name: '황종원', department: '해운정책팀', grade: '직원 3급 이하', role: ROLE.EMPLOYEE },
  { employee_no: 'A2001', name: '이채은', department: '재무회계부', grade: '직원 1·2급', role: ROLE.ADMIN },
]

const KEY = 'nova.session'
const OLD_KEY = 'nova.user'  // 비밀번호 없던 시절(11/9~11/11) 저장값. 보이면 지움

/** 저장된 세션 { token, user }. 없으면 null. */
export function loadSession() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const s = JSON.parse(raw)
    return s?.token && s?.user?.employee_no && s.user.role ? s : null
  } catch {
    return null
  }
}

export function saveSession(session) {
  try { localStorage.removeItem(OLD_KEY); localStorage.setItem(KEY, JSON.stringify({ token: session.token, user: session.user })) } catch { /* 저장 불가 환경이면 세션 동안만 유지 */ }
}

export function clearSession() {
  try { localStorage.removeItem(KEY); localStorage.removeItem(OLD_KEY) } catch { /* 무시 */ }
}

/** 로그인한 사용자 (없으면 null). 화면·API 모듈이 같이 씁니다. */
export function loadUser() {
  return loadSession()?.user ?? null
}

/** 토큰이 거절(401)되면 api/client.js 가 이 이벤트를 띄우고, App 이 로그인 화면으로 돌립니다. */
export const UNAUTHORIZED_EVENT = 'nova:unauthorized'
