// "어떤 정산을 하시나요?" 유형 선택. 유형마다 필요한 서류가 달라서, 고르면 해당 화면으로 안내합니다.
// 유형은 세 가지입니다 (2026-11-13 코칭): 국내출장 / 회의비 / 기타 법인카드 사용. 점심·회식 식대는 회의비에 들어갑니다.
// 국내출장 → 출장비 계산(U-05), 나머지 → 영수증 등록(U-06)에서 시작해 청구 검증(U-04)으로 이어지고,
// 고른 유형은 영수증 등록 화면에 param.claim 으로 넘어갑니다.

import Icon from '../components/Icons.jsx'
import { CLAIM } from '../utils/claimTypes.js'

const TYPES = [
  { id: 'trip', icon: 'trip', title: '국내출장', desc: '교통비·숙박비·일비·식비를 여비규정 기준으로 계산하고 출장보고서까지 준비해요.', docs: '출장원 · 보고서 · 증빙', go: 'travel' },
  { id: 'meeting', icon: 'meeting', title: '회의비', desc: '회의·업무협의 때 쓴 식대와 다과비를 참석자·회의 목적과 함께 정리해요. 점심·회식 식대도 여기서 해요.', docs: '영수증 · 참석자 · 회의 목적', go: 'receipt', param: { claim: CLAIM.MEETING } },
  { id: 'card', icon: 'card', title: '기타 법인카드 사용', desc: '그 밖의 법인카드 사용 내역을 사용 사유와 함께 확인해요.', docs: '영수증 · 사용 사유', go: 'receipt', param: { claim: CLAIM.CARD } },
]

export default function TypePage({ onNavigate }) {
  return (
    <div className="home">
      <h1>어떤 정산을 하시나요?</h1>
      <p className="hint">유형마다 필요한 서류가 달라요. 고르면 다음 단계로 안내해 드려요.</p>
      <div className="tile-grid three">
        {TYPES.map((t) => (
          <button key={t.id} type="button" className="tile" onClick={() => onNavigate(t.go, t.param ?? null)}>
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
