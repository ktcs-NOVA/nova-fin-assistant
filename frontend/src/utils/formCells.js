// 기본 양식(지출 결과서 + 검수확인서)의 칸을 다루는 함수들. 양식 모양은 components/FormSheet.jsx 가 그립니다.

const AI_KEY = /^(detail|use)_\d+$/   // AI 가 제안하는 칸 (그 밖의 고칠 수 있는 칸은 직접 입력)

/** 지금 이 칸의 출처: 직원이 고친 AI 칸은 '직접 입력'으로 바뀜 */
export function sourceOf(cell, fields) {
  if (!cell.key || !fields) return cell.source
  if (!AI_KEY.test(cell.key)) return 'manual'
  const value = String(fields[cell.key] ?? '').trim()
  return !value || (fields.ai_keys ?? []).includes(cell.key) ? 'ai' : 'manual'
}

/** 양식 안의 고칠 수 있는 칸 전부 (안내 목록용) */
export function editableCells(form) {
  return (form?.sheets ?? []).flatMap((sh) => [
    ...sh.table.rows.flat(),
    ...(sh.extra ?? []).map((x) => x.cell),
    ...sh.signers.map((x) => x.cell),
  ]).filter((c) => c.key)
}
