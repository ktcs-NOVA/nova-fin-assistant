// "어떤 정산을 하시나요?" 유형 선택. 유형마다 필요한 서류가 달라서, 고르면 해당 화면으로 안내합니다.
// 지금 연결된 화면: 국내출장 → 출장비 계산(U-05), 나머지 → 영수증 등록(U-06)에서 시작해 청구 검증(U-04)으로 이어집니다.
// 유형별 서류 체크리스트·회의록은 백엔드 서류 API가 생기면 이어 붙입니다.

import Icon from '../components/Icons.jsx'

const TYPES = [
  { id: 'trip', icon: 'trip', title: '국내출장', desc: '교통비·숙박비·일비·식비를 여비규정 기준으로 계산하고 출장보고서까지 준비해요.', docs: '출장원 · 보고서 · 증빙', go: 'travel' },
  { id: 'meal', icon: 'meal', title: '점심·회식', desc: '점심이나 회식 식대가 사용 기준에 맞는지 제출 전에 확인해요.', docs: '영수증 · 참석자 확인', go: 'receipt' },
  { id: 'meeting', icon: 'meeting', title: '회의비', desc: '회의 때 쓴 식대·다과비를 회의록과 함께 정리해요.', docs: '영수증 · 회의록 · 참석자', go: 'receipt' },
  { id: 'card', icon: 'card', title: '기타 법인카드 사용', desc: '그 밖의 법인카드 사용 내역을 사용 사유와 함께 확인해요.', docs: '영수증 · 사용 사유', go: 'receipt' },
]

export default function TypePage({ onNavigate }) {
  return (
    <div className="home">
      <h1>어떤 정산을 하시나요?</h1>
      <p className="hint">유형마다 필요한 서류가 달라요. 고르면 다음 단계로 안내해 드려요.</p>
      <div className="tile-grid two">
        {TYPES.map((t) => (
          <button key={t.id} type="button" className="tile" onClick={() => onNavigate(t.go)}>
            <span className={`tile-icon ico-${t.id}`}><Icon name={t.icon} size={30} /></span>
            <span className="tile-title">{t.title}</span>
            <span className="tile-desc">{t.desc}</span>
            <span className="tile-docs">필요 서류: {t.docs}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
