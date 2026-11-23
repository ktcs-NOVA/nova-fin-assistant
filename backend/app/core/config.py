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

    # RAG
    rag_top_k: int = 5
    rag_min_score: float = 0.3

    # 경로 조회 (POST /api/route) — 네이버 클라우드 플랫폼 Maps (Geocoding · Directions 5)
    # 콘솔 > Maps > Application 등록에서 받은 Client ID / Client Secret. 비어 있으면 거리를 직접 입력하라고 안내
    naver_maps_client_id: str = ""
    naver_maps_client_secret: str = ""
    # 새 Maps 서비스 주소. 예전 AI·NAVER API 로 받은 키라면 https://naveropenapi.apigw.ntruss.com
    naver_maps_base: str = "https://maps.apigw.ntruss.com"
    # (선택) NAVER API HUB 의 지역 검색 Application Client ID / Secret. 넣으면 "부산시청" 같은 장소 이름으로도 찾음
    # (Maps 키와 별개. 예전 네이버 개발자센터 검색 키는 쓸 수 없음)
    naver_search_client_id: str = ""
    naver_search_client_secret: str = ""
    # 출발지 = 근무지. 한국해양진흥공사 본사 (알리오 공시 주소)
    route_origin_address: str = "부산광역시 해운대구 마린시티2로 38"

    @property
    def route_enabled(self) -> bool:
        return bool(self.naver_maps_client_id.strip() and self.naver_maps_client_secret.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_mock(self) -> bool:
        """API 키가 없으면 OpenAI 를 부르지 않고 목업 응답을 씁니다."""
        return not self.openai_api_key.strip()


settings = Settings()
