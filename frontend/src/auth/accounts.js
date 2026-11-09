// 시연용 계정 목록. 백엔드 scripts/seed.py 의 USERS 와 같은 사번·이름·역할이어야 합니다.
// 비밀번호는 없고, 고른 사번을 X-Employee-No 헤더로 보내 백엔드가 그 사람으로 처리합니다.

export const ROLE = { EMPLOYEE: 'employee', ADMIN: 'admin' }
export const ROLE_LABEL = { employee: '직원', admin: '회계 관리자' }

export const ACCOUNTS = [
  { employee_no: 'E1001', name: '노은비', department: '기획팀', grade: '직원 3급 이하', role: ROLE.EMPLOYEE },
  { employee_no: 'E1002', name: '박철환', department: '총무인사부', grade: '직원 1·2급', role: ROLE.EMPLOYEE },
  { employee_no: 'E1003', name: '황종원', department: '해운정책팀', grade: '직원 3급 이하', role: ROLE.EMPLOYEE },
  { employee_no: 'A2001', name: '이채은', department: '재무회계부', grade: '직원 1·2급', role: ROLE.ADMIN },
]

const KEY = 'nova.user'

/** 브라우저에 저장된 로그인 계정. 없으면 null. */
export function loadUser() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const saved = JSON.parse(raw)
    // 목록에 없는 사번(옛 저장값)은 무시
    return ACCOUNTS.find((a) => a.employee_no === saved?.employee_no) ?? null
  } catch {
    return null
  }
}

export function saveUser(account) {
  try { localStorage.setItem(KEY, JSON.stringify({ employee_no: account.employee_no })) } catch { /* 저장 불가 환경이면 세션 동안만 유지 */ }
}

export function clearUser() {
  try { localStorage.removeItem(KEY) } catch { /* 무시 */ }
}
