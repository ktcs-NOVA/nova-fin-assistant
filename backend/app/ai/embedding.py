"""문장 → 벡터 (임베딩)."""

import hashlib
import math
import random

from app.ai.llm import _client
from app.core.config import settings

_BATCH = 100


def _mock_vector(text: str) -> list[float]:
    """키가 없을 때 쓰는 가짜 벡터. 같은 문장이면 항상 같은 벡터 (의미 검색은 안 됨)."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    v = [rng.gauss(0, 1) for _ in range(settings.embedding_dim)]
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """여러 문장을 한 번에 임베딩 (문서 적재용)."""
    if settings.ai_mock:
        return [_mock_vector(t) for t in texts]

    vectors: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        batch = texts[i : i + _BATCH]
        resp = _client().embeddings.create(model=settings.embedding_model, input=batch)
        vectors.extend(d.embedding for d in resp.data)
    return vectors


def embed_query(text: str) -> list[float]:
    """질문 한 개 임베딩 (검색용)."""
    return embed_texts([text])[0]
