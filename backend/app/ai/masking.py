"""외부(OpenAI)로 보내기 전에 개인정보를 가립니다."""

import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # 주민등록번호 900101-1234567
    (re.compile(r"\b\d{6}-?[1-4]\d{6}\b"), "[주민번호]"),
    # 카드번호 1234-5678-9012-3456 / 1234 5678 9012 3456
    (re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"), "[카드번호]"),
    # 휴대전화 010-1234-5678
    (re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b"), "[전화번호]"),
    # 이메일
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[이메일]"),
    # 계좌번호 123-456789-01234 (날짜 2026-10-20 은 건드리지 않도록 마지막 묶음 4자리 이상)
    (re.compile(r"\b\d{3,6}-\d{2,6}-\d{4,8}\b"), "[계좌번호]"),
]


def mask(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text
