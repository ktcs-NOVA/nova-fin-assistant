@echo off
chcp 65001 >nul
rem 백엔드 서버 켜기 (DB 자동 켜기 + 테이블 최신화 포함). 끄기: Ctrl+C
cd /d "%~dp0"
set PYTHONUTF8=1
set UV_LINK_MODE=copy

docker compose up -d --wait >nul 2>&1 || goto :nodb
uv run alembic upgrade head || exit /b 1

echo.
echo 서버: http://localhost:8000      API 테스트: http://localhost:8000/docs
echo.
uv run uvicorn app.main:app --reload
exit /b

:nodb
echo DB 를 켜지 못했습니다. Docker Desktop 이 실행 중인지 확인해 주세요.
exit /b 1
