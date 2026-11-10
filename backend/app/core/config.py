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
