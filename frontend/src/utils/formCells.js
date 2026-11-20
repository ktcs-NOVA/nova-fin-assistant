// 기본 양식(지출 결과서 · 회의록 · 출장보고서)의 칸을 다루는 함수들. 양식 모양은 components/FormSheet.jsx 가 그립니다.
// 양식 한 부 = 장(sheet) 여러 개, 한 장 = 블록(info · table · field · note · signers · evidence · photos) 목록
// (칸 구성은 백엔드 domains/documents/forms.py 가 정합니다).

/** 지금 이 칸의 출처. 고칠 수 있는 칸은 값이 AI 가 쓴 그대로면 'ai', 직원이 적었으면 'manual' */
export function sourceOf(cell, fields) {
  if (!cell.key || !fields) return cell.source
  const value = String(fields[cell.key] ?? '').trim()
  if (!value) return cell.ai ? 'ai' : 'manual'
  return (fields.ai_keys ?? []).includes(cell.key) ? 'ai' : 'manual'
}

/** 한 블록 안의 칸들 */
export function blockCells(block) {
  if (block.type === 'info' || block.type === 'signers') return block.rows.map((r) => r.cell)
  if (block.type === 'table') return block.rows.flat()
  if (block.type === 'field') return [block.cell]
  return []
}

/**
 * "작성하기" 화면용: 고칠 수 있는 칸마다 어느 장의 어떤 줄인지 붙여서 돌려줍니다.
 * 표 안의 칸이면 같은 줄의 품명·금액을 ctx 로, 그 칸의 열 이름(상세내역·용도)을 name 으로 씁니다.
 */
export function editableWithContext(form) {
  const out = []
  for (const sh of form?.sheets ?? []) {
    for (const b of sh.blocks) {
      if (b.type === 'table') {
        const labels = b.columns.map((c) => c.label)
        const pick = (row, re) => { const i = labels.findIndex((l) => re.test(l)); return i >= 0 ? String(row[i]?.value ?? '') : '' }
        b.rows.forEach((row) => row.forEach((cell, j) => {
          if (!cell.key) return
          const item = pick(row, /품명/)
          const amount = pick(row, /^금액/)
          out.push({ ...cell, sheet: sh.title, name: labels[j], ctx: [item, amount && (amount.endsWith('원') ? amount : `${amount}원`)].filter(Boolean).join(' · ') })
        }))
      } else {
        blockCells(b).filter((c) => c.key).forEach((cell) => out.push({ ...cell, sheet: sh.title, name: cell.label, ctx: '' }))
      }
    }
  }
  return out
}

/** 양식 첫 장의 머리표(건명·부서 …) — 작성하기 화면 위쪽 요약용 */
export function formSummary(form) {
  const info = form?.sheets?.[0]?.blocks.find((b) => b.type === 'info')
  const total = form?.sheets?.[0]?.blocks.find((b) => b.type === 'table' && b.total)?.total
  const rows = (info?.rows ?? []).filter((r) => !r.cell.key).map((r) => ({ label: r.label, value: String(r.cell.value ?? '') }))
  return total ? [...rows, { label: '합계', value: total.value }] : rows
}

/** 양식 안의 고칠 수 있는 칸 전부 (안내 목록용, 위에서 아래 순서) */
export function editableCells(form) {
  return (form?.sheets ?? []).flatMap((sh) => sh.blocks.flatMap(blockCells)).filter((c) => c.key)
}
