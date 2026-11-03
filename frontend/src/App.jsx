import { useState } from 'react'
import Layout from './components/Layout.jsx'
import QaPage from './pages/QaPage.jsx'
import VerifyPage from './pages/VerifyPage.jsx'
import ChecklistPage from './pages/ChecklistPage.jsx'

// 메뉴 목록. 화면을 추가하려면 여기에 한 줄 추가하고 pages/ 에 파일을 만들면 됩니다.
const PAGES = [
  { id: 'qa', label: '규정 Q&A', component: QaPage },
  { id: 'verify', label: '청구 검증', component: VerifyPage },
  { id: 'checklist', label: '체크리스트', component: ChecklistPage },
]

export default function App() {
  const [current, setCurrent] = useState('verify')
  const Page = PAGES.find((p) => p.id === current).component

  return (
    <Layout pages={PAGES} current={current} onChange={setCurrent}>
      <Page />
    </Layout>
  )
}
