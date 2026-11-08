import { useState } from 'react'
import Layout from './components/Layout.jsx'
import QaPage from './pages/QaPage.jsx'
import VerifyPage from './pages/VerifyPage.jsx'
import ChecklistPage from './pages/ChecklistPage.jsx'
import ReceiptPage from './pages/ReceiptPage.jsx'
import TravelCalcPage from './pages/TravelCalcPage.jsx'
import ReviewPage from './pages/admin/ReviewPage.jsx'

// 역할별 메뉴. 화면을 추가하려면 해당 역할 목록에 한 줄 추가하고 pages/ 에 파일을 만들면 됩니다.
// 실제 로그인은 없고, 헤더의 역할 전환으로 시연합니다.
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
  const [role, setRole] = useState('admin')
  const [current, setCurrent] = useState(MENUS.admin.home)
  // 영수증 등록(U-06)·출장비 계산(U-05)에서 "청구 검증으로 보내기"를 누르면 여기에 담겨 청구 검증(U-04) 폼의 초기값이 됩니다.
  const [verifyPrefill, setVerifyPrefill] = useState(null)

  const menu = MENUS[role]
  const Page = (menu.pages.find((p) => p.id === current) ?? menu.pages[0]).component

  function changeRole(next) {
    setRole(next)
    setCurrent(MENUS[next].home)
    setVerifyPrefill(null)
  }

  function changePage(id) {
    setCurrent(id)
    if (id !== 'verify') setVerifyPrefill(null)   // 검증 화면을 떠나면 넘겨받은 값은 버림
  }

  function sendToVerify(prefill) {
    setVerifyPrefill(prefill)
    setRole('employee')
    setCurrent('verify')
  }

  return (
    <Layout
      roles={Object.entries(MENUS).map(([id, m]) => ({ id, label: m.label }))}
      role={role}
      onRoleChange={changeRole}
      pages={menu.pages}
      current={current}
      onChange={changePage}
    >
      <Page onNavigate={changePage} onSendToVerify={sendToVerify} prefill={verifyPrefill} />
    </Layout>
  )
}
