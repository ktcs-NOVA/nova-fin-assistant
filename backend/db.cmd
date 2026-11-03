@echo off
chcp 65001 >nul
rem DB 관리:  db.cmd  = 켜기 / db.cmd stop = 끄기 / db.cmd reset = 데이터 전부 삭제
cd /d "%~dp0"

if /i "%~1"=="stop" goto :stop
if /i "%~1"=="reset" goto :reset

docker compose up -d --wait && echo DB 켜짐: localhost:5432
exit /b

:stop
docker compose down && echo DB 꺼짐. 데이터는 남아 있습니다.
exit /b

:reset
docker compose down -v && echo DB 데이터를 모두 지웠습니다. setup.cmd 를 다시 실행하세요.
exit /b
