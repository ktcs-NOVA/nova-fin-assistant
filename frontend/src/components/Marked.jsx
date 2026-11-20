// 글자 안에서 검색어를 <mark> 로 강조합니다. 검색어가 없으면 글자 그대로.

export default function Marked({ text, query }) {
  const q = query?.trim()
  if (!q || !text) return text ?? null
  const parts = text.split(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'))
  return parts.map((part, i) => (i % 2 ? <mark key={i}>{part}</mark> : part))
}
