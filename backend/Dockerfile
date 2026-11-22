# NOVA 백엔드 (FastAPI) 운영 이미지
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

ENV PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 패키지만 먼저 설치해 두면 코드만 바뀔 때 이 단계를 다시 하지 않습니다
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000
# 켤 때마다 마이그레이션을 맞춘 뒤 서버를 띄웁니다 (이미 최신이면 아무 일도 안 함)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
