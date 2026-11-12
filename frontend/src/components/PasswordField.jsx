// 비밀번호 입력칸 + 오른쪽 눈 아이콘(누르면 글자가 보이고, 다시 누르면 가려짐).

import { useState } from 'react'
import Icon from './Icons.jsx'

export default function PasswordField({ value, onChange, autoComplete, placeholder }) {
  const [show, setShow] = useState(false)
  return (
    <span className="pw-wrap">
      <input type={show ? 'text' : 'password'} value={value} onChange={onChange} autoComplete={autoComplete} placeholder={placeholder} />
      <button type="button" className="pw-eye" onClick={() => setShow((s) => !s)} aria-label={show ? '비밀번호 숨기기' : '비밀번호 보기'} aria-pressed={show}>
        <Icon name={show ? 'eyeOff' : 'eye'} size={20} />
      </button>
    </span>
  )
}
