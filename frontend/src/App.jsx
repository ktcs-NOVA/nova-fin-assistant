import { useEffect, useState } from 'react'
import Layout from './components/Layout.jsx'
import LoginPage from './pages/LoginPage.jsx'
import QaPage from './pages/QaPage.jsx'
import VerifyPage from './pages/VerifyPage.jsx'
import ChecklistPage from './pages/ChecklistPage.jsx'
import ReceiptPage from './pages/ReceiptPage.jsx'
import TravelCalcPage from './pages/TravelCalcPage.jsx'
import ReviewPage from './pages/admin/ReviewPage.jsx'
import { loadSession, saveSession, clearSession, UNAUTHORIZED_EVENT } from './auth/accounts.js'

// 역할별 메뉴. 화면을 추가하려면 해당 역할 목록에 한 줄 추가하고 pages/ 에 파일을 만들면 됩니다.
// 어느 역할 화면으로 들어갈지는 로그인(계정 선택)에서 정해지고, 안에서는 역할을 바꿀 수 없습니다.
const MENUS = {
  employee: {
    label: '직원',
    pages: [
      { id: 'receipt', label: '영수증 등록', component: ReceiptPage },  // U-06
      { id: 'qa', label: '규정 Q&A', component: QaPage },            // U-01
      { id: 'travel', label: '출장비 계산', component: TravelCalcPage }, // U-05
      { id: 'verify', label: '청구 검증', component: VerifyPage },    // U-04
      { id: 'checklist', label: '체크리스트', component: ChecklistPage },
    ],
    home: 'verify',
  },
  admin: {
    label: '회계 관리자',
    pages: [
      { id: 'review', label: '정산 검토', component: ReviewPage },     // M-01
    ],
    home: 'review',
  },
}

export default function App() {
  const [user, setUser] = useState(() => loadSession()?.user ?? null)   // 로그인한 계정 (토큰과 함께 브라우저에 기억)
  const [current, setCurrent] = useState(() => (user ? MENUS[user.role].home : null))
  // 영수증 등록(U-06)·출장비 계산(U-05)에서 "청구 검증으로 보내기"를 누르면 여기에 담겨 청구 검증(U-04) 폼의 초기값이 됩니다.
  const [verifyPrefill, setVerifyPrefill] = useState(null)

  // 로그인·회원가입 응답 { token, user } 를 저장하고 역할에 맞는 첫 화면으로
  function login(session) {
    saveSession(session)
    setUser(session.user)
    setCurrent(MENUS[session.user.role].home)
    setVerifyPrefill(null)
  }

  function logout() {
    clearSession()
    setUser(null)
    setCurrent(null)
    setVerifyPrefill(null)
  }

  // API 가 토큰을 거절(401)하면 client.js 가 이 이벤트를 띄움 → 로그인 화면으로
  useEffect(() => {
    window.addEventListener(UNAUTHORIZED_EVENT, logout)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, logout)
  }, [])

  if (!user) return <LoginPage onLogin={login} />

  const menu = MENUS[user.role]
  const Page = (menu.pages.find((p) => p.id === current) ?? menu.pages[0]).component

  function changePage(id) {
    setCurrent(id)
    if (id !== 'verify') setVerifyPrefill(null)   // 검증 화면을 떠나면 넘겨받은 값은 버림
  }

  function sendToVerify(prefill) {
    setVerifyPrefill(prefill)
    setCurrent('verify')
  }

  return (
    <Layout user={user} roleLabel={menu.label} onLogout={logout} pages={menu.pages} current={current} onChange={changePage}>
      <Page onNavigate={changePage} onSendToVerify={sendToVerify} prefill={verifyPrefill} />
    </Layout>
  )
}
