import { useState } from 'react'
import Layout from './components/Layout.jsx'
import QaPage from './pages/QaPage.jsx'
import VerifyPage from './pages/VerifyPage.jsx'
import ChecklistPage from './pages/ChecklistPage.jsx'
import ReceiptPage from './pages/ReceiptPage.jsx'
import ReviewPage from './pages/admin/ReviewPage.jsx'

// 역할별 메뉴. 화면을 추가하려면 해당 역할 목록에 한 줄 추가하고 pages/ 에 파일을 만들면 됩니다.
// 실제 로그인은 없고, 헤더의 역할 전환으로 시연합니다.
const MENUS = {
  employee: {
    label: '직원',
    pages: [
      { id: 'receipt', label: '영수증 등록', component: ReceiptPage },  // U-06
      { id: 'qa', label: '규정 Q&A', component: QaPage },            // U-01
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

  const menu = MENUS[role]
  const Page = (menu.pages.find((p) => p.id === current) ?? menu.pages[0]).component

  function changeRole(next) {
    setRole(next)
    setCurrent(MENUS[next].home)
  }

  return (
    <Layout
      roles={Object.entries(MENUS).map(([id, m]) => ({ id, label: m.label }))}
      role={role}
      onRoleChange={changeRole}
      pages={menu.pages}
      current={current}
      onChange={setCurrent}
    >
      <Page />
    </Layout>
  )
}
