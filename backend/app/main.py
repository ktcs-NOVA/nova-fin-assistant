"""FastAPI 앱 시작점.

uv run uvicorn app.main:app --reload
→ http://localhost:8000/docs  (API 테스트 화면)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.core.errors import register_error_handlers
from app.domains.checklist.router import router as checklist_router
from app.domains.qa.router import router as qa_router
from app.domains.verify import service as verify_service
from app.domains.verify.router import router as verify_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="NOVA 경비 정산 사전검증 API",
    version="0.1.0",
    description="팀 NOVA · 한국해양진흥공사 경비 규정 기반 사전검증 에이전트",
)

# 순서 중요: 에러 처리를 먼저, CORS 를 나중에 등록해야 에러 응답에도 CORS 헤더가 붙음
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["상태 확인"], summary="서버 · DB · AI 상태")
def health() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db = "ok"
    except Exception:
        db = "error"
    return {
        "status": "ok",
        "db": db,
        "ai": "mock" if settings.ai_mock else "openai",
        "verify_engine": "precheck" if verify_service.engine_available() else "sample",
    }


# ---------- 기능 라우터 등록: 새 기능은 여기 한 줄 ----------
app.include_router(qa_router)  # POST /api/qa
app.include_router(verify_router)  # POST /api/verify  (규칙 엔진 연결)
app.include_router(checklist_router)  # GET  /api/checklist
