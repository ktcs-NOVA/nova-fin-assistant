// 이메일 입력: "아이디 @ [도메인 선택]". 도메인은 목록에서 고르고, 없으면 '직접 입력'을 고르면 직접 쓸 수 있어요.
// 부모에는 합쳐진 전체 주소(아이디@도메인)를 문자열로 돌려줍니다. 둘 중 하나가 비면 빈 문자열.

import { useState } from 'react'

const EMAIL_DOMAINS = ['gmail.com', 'naver.com', 'kakao.com', 'daum.net', 'hanmail.net', 'outlook.com', 'kobc.example']
const CUSTOM = '__custom__'

export default function EmailField({ onChange }) {
  const [local, setLocal] = useState('')
  const [domain, setDomain] = useState(EMAIL_DOMAINS[0])
  const [custom, setCustom] = useState('')

  function emit(l, d, c) {
    const dom = (d === CUSTOM ? c : d).trim()
    onChange(l.trim() && dom ? `${l.trim()}@${dom}` : '')
  }

  return (
    <span className="email-wrap">
      <input type="text" value={local} autoComplete="username" placeholder="아이디"
        onChange={(e) => { setLocal(e.target.value); emit(e.target.value, domain, custom) }} aria-label="이메일 아이디" />
      <span className="email-at" aria-hidden="true">@</span>
      {domain === CUSTOM ? (
        <input type="text" value={custom} placeholder="직접 입력 (예: company.kr)" aria-label="이메일 도메인 직접 입력"
          onChange={(e) => { setCustom(e.target.value); emit(local, domain, e.target.value) }} />
      ) : null}
      <select value={domain} aria-label="이메일 도메인"
        onChange={(e) => { setDomain(e.target.value); emit(local, e.target.value, custom) }}>
        {EMAIL_DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
        <option value={CUSTOM}>직접 입력</option>
      </select>
    </span>
  )
}
