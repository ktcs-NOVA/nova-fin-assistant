"""답변 생성 (LLM)."""

from functools import lru_cache

from app.ai.masking import mask
from app.core.config import settings


@lru_cache
def _client():
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


def chat(system: str, user: str, *, temperature: float | None = 0.0) -> str:
    """시스템 지시문 + 사용자 메시지 → 답변 문자열.

    user 메시지는 보내기 전에 마스킹됩니다.
    temperature 를 지원하지 않는 모델을 쓰면 None 으로 넘기세요.
    """
    user = mask(user)

    if settings.ai_mock:
        return "[목업 AI] OPENAI_API_KEY 가 없어 실제 답변 대신 이 문장을 돌려줍니다."

    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    resp = _client().chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **kwargs,
    )
    return resp.choices[0].message.content or ""
