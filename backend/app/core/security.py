"""비밀번호 해시와 로그인 토큰. 외부 라이브러리 없이 표준 라이브러리만 씁니다.

- 비밀번호: PBKDF2-SHA256 (반복 횟수·소금·해시를 한 문자열에 보관)
- 토큰: "사번.만료시각.서명" — 서명은 AUTH_SECRET 으로 만든 HMAC-SHA256.
  서버가 토큰을 저장하지 않으므로 비밀 값이 바뀌면 모든 로그인이 풀립니다.
"""

import base64
import hashlib
import hmac
import secrets
import time

from app.core.config import settings

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        algo, iterations, salt, expected = stored.split("$", 3)
    except ValueError:
        return False
    if algo != _ALGO:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations))
    return hmac.compare_digest(digest.hex(), expected)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _sign(payload: str) -> str:
    return _b64(hmac.new(settings.auth_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest())


def create_token(employee_no: str, now: float | None = None) -> str:
    expires = int((now or time.time()) + settings.auth_token_days * 86400)
    payload = f"{_b64(employee_no.encode('utf-8'))}.{expires}"
    return f"{payload}.{_sign(payload)}"


def read_token(token: str, now: float | None = None) -> str | None:
    """토큰이 올바르고 만료 전이면 사번, 아니면 None."""
    try:
        enc_no, expires, signature = token.strip().split(".")
        payload = f"{enc_no}.{expires}"
        if not hmac.compare_digest(_sign(payload), signature):
            return None
        if int(expires) < (now or time.time()):
            return None
        padded = enc_no + "=" * (-len(enc_no) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
