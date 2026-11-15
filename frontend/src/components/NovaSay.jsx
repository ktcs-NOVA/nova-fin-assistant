// NOVA 마스코트(돋보기를 든 모습)가 대답하는 것처럼 보이는 말풍선: 왼쪽에 마스코트, 오른쪽에 말풍선
// loading 이면 마스코트가 통통 튀며 "찾아보고 있어요" 를 보여 줍니다.
// 규정 물어보기 화면(QaPage)과 정산 화면의 질문창(AskDock)이 함께 씁니다.

import seeker from '../assets/nova-seeker.png'

export default function NovaSay({ loading = false, children }) {
  return (
    <div className={`nova-row ${loading ? 'thinking' : ''}`}>
      <img className="nova-avatar" src={seeker} alt="" />
      <div className="nova-main">
        <span className="nova-name">NOVA</span>
        <div className="bubble-bot">
          {loading ? <p className="loading">규정을 찾아보고 있어요<span className="dots" aria-hidden="true" /></p> : children}
        </div>
      </div>
    </div>
  )
}
