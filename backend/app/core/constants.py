"""여러 기능이 같이 쓰는 고정 값. 프론트(frontend/src/api/client.js)와 글자까지 같아야 합니다."""

from typing import Literal

# 판정 값 3가지 (docs/API.md 3-2)
VERDICT_OK = "규정상 확인 가능"
VERDICT_FIX = "보완 필요"
VERDICT_CHECK = "담당자 확인 필요"
# 근거를 못 찾았을 때 안내할 담당자 계정 (scripts/seed.py 의 데모담당자)
CONTACT_EMPLOYEE_NO = "A2002"
Verdict = Literal["규정상 확인 가능", "보완 필요", "담당자 확인 필요"]

# 정산 제출 건의 검토 상태 (frontend client.js 의 STATUS)
STATUS_PENDING = "검토 대기"
STATUS_APPROVED = "승인"
STATUS_REJECTED = "반려"

# 사용자 역할
ROLE_EMPLOYEE = "employee"
ROLE_ADMIN = "admin"

# 문서를 볼 수 있는 대상
AUDIENCE_ALL = "all"
AUDIENCE_EMPLOYEE = "employee"
AUDIENCE_ADMIN = "admin"
