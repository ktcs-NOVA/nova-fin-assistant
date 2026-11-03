"""외부 AI 연결 지점. OpenAI 호출은 반드시 이 폴더를 통해서만 합니다.

    from app.ai import chat, embed_texts, embed_query

- 외부로 나가기 전에 개인정보 마스킹(masking.py)을 거칩니다.
- OPENAI_API_KEY 가 없으면 목업 응답으로 동작합니다 (팀원 누구나 키 없이 실행 가능).
- 나중에 사내 모델로 바꿀 때는 이 폴더만 고치면 됩니다.
"""

from app.ai.embedding import embed_query, embed_texts
from app.ai.llm import chat
from app.ai.masking import mask

__all__ = ["chat", "embed_query", "embed_texts", "mask"]
