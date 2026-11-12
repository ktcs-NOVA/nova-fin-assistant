import { useEffect, useState } from 'react'
import Layout from './components/Layout.jsx'
import LoginPage from './pages/LoginPage.jsx'
import HomePage from './pages/HomePage.jsx'
import TypePage from './pages/TypePage.jsx'
import MyStatusPage from './pages/MyStatusPage.jsx'
import QaPage from './pages/QaPage.jsx'
import VerifyPage from './pages/VerifyPage.jsx'
import ChecklistPage from './pages/ChecklistPage.jsx'
import ReceiptPage from './pages/ReceiptPage.jsx'
import TravelCalcPage from './pages/TravelCalcPage.jsx'
import AdminHomePage from './pages/admin/AdminHomePage.jsx'
import ReviewPage from './pages/admin/ReviewPage.jsx'
import { loadSession, saveSession, clearSession, UNAUTHORIZED_EVENT } from './auth/accounts.js'

// 화면 목록. 화면을 추가하려면 해당 역할의 pages 에 한 줄 넣고 pages/ 에 파일을 만들면 됩니다.
// parent: 빵부스러기(현재 위치)에서 한 단계 위 화면. 없으면 맨 위(홈).
// 어느 역할 화면으로 들어갈지는 로그인에서 정해지고, 안에서는 역할을 바꿀 수 없습니다.
const MENUS = {
  employee: {
    label: '직원',
    home: 'home',
    pages: {
      home: { label: '홈', component: HomePage },
      type: { label: '정산하기', component: TypePage, parent: 'home' },
      receipt: { label: '영수증 등록', component: ReceiptPage, parent: 'type' },     // U-06
      travel: { label: '출장비 계산', component: TravelCalcPage, parent: 'type' },   // U-05
      verify: { label: '청구 검증', component: VerifyPage, parent: 'type' },         // U-04
      mystatus: { label: '내 정산 현황', component: MyStatusPage, parent: 'home' },
      checklist: { label: '문서 작업', component: ChecklistPage, parent: 'home' }, // U-02
      qa: { label: '규정 물어보기', component: QaPage, parent: 'home' },             // U-01
    },
  },
  admin: {
    label: '회계 관리자',
    home: 'adminhome',
    pages: {
      adminhome: { label: '홈', component: AdminHomePage },
      review: { label: '검토 대기', component: ReviewPage, parent: 'adminhome' },   // M-01
      qa: { label: '규정 물어보기', component: QaPage, parent: 'adminhome' },
    },
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
  const pageId = menu.pages[current] ? current : menu.home
  const Page = menu.pages[pageId].component

  // 빵부스러기: 홈 > 정산하기 > 출장비 계산 처럼 현재 화면까지의 길
  const crumbs = []
  for (let id = pageId; id; id = menu.pages[id].parent) {
    crumbs.unshift({ id, label: menu.pages[id].label, go: () => changePage(id) })
  }

  function changePage(id) {
    setCurrent(id)
    if (id !== 'verify') setVerifyPrefill(null)   // 검증 화면을 떠나면 넘겨받은 값은 버림
    window.scrollTo?.(0, 0)
  }

  function sendToVerify(prefill) {
    setVerifyPrefill(prefill)
    setCurrent('verify')
  }

  return (
    <Layout user={user} roleLabel={menu.label} onLogout={logout} onHome={() => changePage(menu.home)} onAsk={() => changePage('qa')} crumbs={crumbs}>
      <Page user={user} onNavigate={changePage} onSendToVerify={sendToVerify} prefill={verifyPrefill} />
    </Layout>
  )
}
