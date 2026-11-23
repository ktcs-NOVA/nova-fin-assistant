#!/bin/sh
# 처음 배포할 때 한 번: 계정·시연 데이터 넣기 + 규정 문서 적재
# (테이블은 백엔드가 켜질 때 alembic 으로 자동 생성됩니다)
#   sh deploy/init.sh
set -e
cd "$(dirname "$0")/.."
DC="docker compose -f docker-compose.prod.yml --env-file .env.prod"

echo "[1/4] 계정 + 예시 제출 건"
$DC exec -T backend python -m scripts.seed
echo "[2/4] 관리자 검토함 시연 데이터"
$DC exec -T backend python -m scripts.seed_demo
echo "[3/4] 직원 규정 (hwpx)"
$DC exec -T backend sh -c 'python -m scripts.ingest data/regulations/*.hwpx'
echo "[4/4] 관리자 전용 규정 (hwp)"
$DC exec -T backend sh -c 'python -m scripts.ingest --audience admin data/regulations/*.hwp'
echo "완료"
