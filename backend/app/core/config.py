"""환경 설정. backend/.env 값을 읽어 settings 객체로 제공합니다. (Spring 의 application.yml 역할)

from app.core.config import settings
settings.database_url
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # DB
    database_url: str = "postgresql+psycopg://nova:nova@localhost:5432/nova"

    # 프론트 개발 서버 (쉼표로 여러 개)
    cors_origins: str = "http://localhost:5173"

    # OpenAI (비어 있으면 목업 AI)
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    # 영수증 사진 판독 모델. 11장 측정(2026-11-10)에서 gpt-4o 와 정답률이 같아(89%) 싼 쪽을 기본으로 둡니다
    receipt_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    # 임베딩 차원은 DB 컬럼 크기와 같아야 함 (models/knowledge.py, alembic 마이그레이션)
    embedding_dim: int = 1536

    # 로그인 (POST /api/auth/*). 토큰 서명용 비밀 값 — 운영에서는 반드시 바꿀 것
    auth_secret: str = "nova-dev-secret-change-me"
    auth_token_days: int = 7

    # 경로 조회 (POST /api/route): 네이버 클라우드 플랫폼 Maps 의 Geocoding · Directions 5.
    # 비어 있으면 경로 조회는 503 으로 "설정되지 않음"을 알리고, 화면은 거리를 직접 입력하게 합니다.
    naver_maps_key_id: str = ""
    naver_maps_key: str = ""
    # (선택) 네이버 검색 API(지역) — "부산시청" 같은 장소 이름으로도 찾고 싶을 때. 없으면 주소로만 찾습니다.
    naver_search_client_id: str = ""
    naver_search_client_secret: str = ""
    # 출발지(회사) 주소 — ALIO 공시 기준 한국해양진흥공사 본사
    route_origin_address: str = "부산광역시 해운대구 마린시티2로 38"

    # RAG
    rag_top_k: int = 5
    rag_min_score: float = 0.3

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_mock(self) -> bool:
        """API 키가 없으면 OpenAI 를 부르지 않고 목업 응답을 씁니다."""
        return not self.openai_api_key.strip()


settings = Settings()
