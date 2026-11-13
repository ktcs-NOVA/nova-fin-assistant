// 관리자 숫자 카드 3종: 제출 / 검토 대기 / 확인 필요. 누르면 그 보기로 바뀝니다 (onPick).
// "확인 필요"는 빨간 배경 + ⚠ 로 눈에 띄게 (2026-11-13 코칭). counts 는 pages/admin/reviewQueue.js 의 countQueue 결과.

import Icon from './Icons.jsx'

export default function ReviewStats({ counts, active, onPick, big = false }) {
  const n = (v) => (counts ? `${v}건` : '…')
  const parts = counts ? [
    counts.fix && `보완 필요 ${counts.fix}`,
    counts.check && `담당자 확인 ${counts.check}`,
    counts.account && `계정과목 ${counts.account}`,
    counts.rejected && `반려 ${counts.rejected}`,
  ].filter(Boolean) : []
  const cards = [
    { view: 'all', label: '제출', value: counts?.total, sub: counts ? `승인 완료 ${counts.approved}건 포함` : '' },
    { view: 'pending', label: '검토 대기', value: counts?.pending, sub: '아직 승인·반려하지 않은 건' },
    { view: 'needs', label: '확인 필요', value: counts?.needs, sub: parts.join(' · ') || (counts ? '지금은 없어요' : ''), alert: true },
  ]
  return (
    <div className={`stat-row${big ? ' big' : ''}`}>
      {cards.map((c) => (
        <button
          key={c.view}
          type="button"
          className={`stat${c.alert && (!counts || c.value > 0) ? ' alert' : ''}${active === c.view ? ' on' : ''}`}
          aria-pressed={active ? active === c.view : undefined}
          onClick={() => onPick(c.view)}
        >
          <span className="stat-label">{c.alert && <Icon name="warn" size={big ? 18 : 15} />}{c.label}</span>
          <span className="stat-value">{n(c.value)}</span>
          {big && <span className="stat-sub">{c.sub}</span>}
        </button>
      ))}
    </div>
  )
}
