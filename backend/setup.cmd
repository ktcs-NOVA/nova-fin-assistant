@echo off
chcp 65001 >nul
rem 처음 한 번: DB 켜기 + 테이블 생성 + 데모 데이터 + 규정 적재
cd /d "%~dp0"
set PYTHONUTF8=1
set UV_LINK_MODE=copy

if not exist .env (
  copy .env.example .env >nul
  echo [안내] .env 파일을 만들었습니다. OPENAI_API_KEY 를 넣으면 실제 AI 로 동작합니다.
)

echo [1/4] DB 켜는 중...
docker compose up -d --wait || goto :fail
echo [2/4] 패키지 설치 + 테이블 생성...
uv run alembic upgrade head || goto :fail
echo [3/4] 데모 데이터 넣는 중...
uv run python -m scripts.seed || goto :fail
echo [4/4] 규정 문서 적재 중...
uv run python -m scripts.ingest || goto :fail

echo.
echo 완료! 이제 server.cmd 로 서버를 켜세요.
exit /b 0

:fail
echo.
echo 실패했습니다. 위 메시지를 확인해 주세요. Docker Desktop 이 켜져 있는지도 확인해 주세요.
exit /b 1
