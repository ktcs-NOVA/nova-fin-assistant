"""규칙 엔진 — U-04 사전검증 · U-05 출장비 계산 · U-07 결의서 초안.

지금 엔진 코드는 feature/u04-precheck 계열 브랜치의 backend/precheck/ 에 있습니다.
그 브랜치를 합칠 때 이 폴더로 옮깁니다.

    git mv backend/precheck/* backend/app/precheck/
    # 테스트 import 수정: from precheck import …  →  from app.precheck import …

옮기고 나면 app/domains/verify 가 자동으로 이 엔진을 사용합니다.
"""
