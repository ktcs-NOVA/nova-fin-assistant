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

/** 양식 안의 고칠 수 있는 칸 전부 (안내 목록용, 위에서 아래 순서) */
export function editableCells(form) {
  return (form?.sheets ?? []).flatMap((sh) => sh.blocks.flatMap(blockCells)).filter((c) => c.key)
}
