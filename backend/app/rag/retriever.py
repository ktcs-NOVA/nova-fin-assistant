"""검색: 질문과 가까운 조각을 찾습니다. 의미 검색 + 키워드 검색을 섞은 하이브리드 검색.

1. 일상어 사전으로 검색어 보강 (법카 → 법인카드, 회의비 → 업무추진비)
2. 의미 검색 (pgvector 코사인 거리) 후보 + 키워드 검색 (낱말을 글자 2개씩 자른 BM25) 후보
3. 두 순위를 RRF(순위 역수 합)로 합침 — "노래방", "23시"처럼 단어가 맞아야 하는 질문 대응
4. 같은 조항에서 나온 조각은 최대 2개까지만 — 전결표 별표 조각(700여 개)이 결과를 독점하지 않도록

점수(Hit.score)는 그대로 코사인 유사도라서 답변 쪽 기준(RAG_MIN_SCORE)은 바뀌지 않습니다.
"""

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import embed_query
from app.core.config import settings
from app.core.constants import AUDIENCE_ALL
from app.models import Chunk, Document
from app.rag.synonyms import expand

DEFAULT_TYPES = ("article", "table")  # 서식(form)은 기본 검색에서 제외
CANDIDATES = 40  # 의미·키워드 검색에서 각각 가져올 후보 수
PER_ARTICLE = 2  # 같은 조항에서 결과에 넣을 최대 조각 수
RRF_K = 60  # RRF 상수 (일반적으로 쓰는 값)

_WORD = re.compile(r"[0-9a-z가-힣]+")


@dataclass
class Hit:
    chunk: Chunk
    document: Document
    score: float  # 코사인 유사도 (1에 가까울수록 비슷)


def has_documents(db: Session) -> bool:
    return (db.scalar(select(func.count()).select_from(Chunk)) or 0) > 0


# ---------- 키워드 검색 (글자 2개 단위 BM25) ----------


def bigrams(text: str) -> list[str]:
    """낱말마다 글자 2개씩 자릅니다. 형태소 분석 없이도 '노래방', '23시'가 맞춰집니다.

    낱말 경계를 넘는 조각('출장 때' → '장때')은 만들지 않아 엉뚱한 일치를 줄입니다.
    """
    return [w[i : i + 2] for w in _WORD.findall(text.lower()) for i in range(len(w) - 1)]


@dataclass
class KeywordIndex:
    ids: list[int]
    tfs: list[Counter]
    lengths: list[int]
    df: Counter = field(default_factory=Counter)

    @classmethod
    def build(cls, rows: Sequence[tuple[int, str]]) -> "KeywordIndex":
        ids, tfs, lengths, df = [], [], [], Counter()
        for chunk_id, text in rows:
            tf = Counter(bigrams(text))
            ids.append(chunk_id)
            tfs.append(tf)
            lengths.append(sum(tf.values()) or 1)
            df.update(tf.keys())
        return cls(ids, tfs, lengths, df)

    def search(self, query: str, limit: int, *, k1: float = 1.2, b: float = 0.75) -> list[int]:
        n = len(self.ids)
        if not n:
            return []
        avg = sum(self.lengths) / n
        terms = set(bigrams(query))
        idf = {
            t: math.log(1 + (n - self.df[t] + 0.5) / (self.df[t] + 0.5))
            for t in terms
            if t in self.df
        }
        scored = []
        for chunk_id, tf, length in zip(self.ids, self.tfs, self.lengths):
            s = 0.0
            for t, w in idf.items():
                f = tf.get(t)
                if f:
                    s += w * f * (k1 + 1) / (f + k1 * (1 - b + b * length / avg))
            if s > 0:
                scored.append((s, chunk_id))
        scored.sort(reverse=True)
        return [chunk_id for _, chunk_id in scored[:limit]]


_index_cache: dict[tuple, KeywordIndex] = {}


def _keyword_index(db: Session, audience: str | None, chunk_types: Sequence[str]) -> KeywordIndex:
    """키워드 색인은 조각이 바뀔 때만 다시 만듭니다 (조각 수 · 마지막 id 로 판단)."""
    count, last_id = db.execute(select(func.count(Chunk.id), func.max(Chunk.id))).one()
    key = (count, last_id, audience, tuple(chunk_types))
    if key not in _index_cache:
        stmt = (
            select(Chunk.id, Document.title, Chunk.article, Chunk.article_title, Chunk.content)
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.is_current.is_(True), Chunk.chunk_type.in_(chunk_types))
        )
        if audience:
            stmt = stmt.where(Document.audience.in_([AUDIENCE_ALL, audience]))
        rows = [(cid, " ".join(filter(None, parts))) for cid, *parts in db.execute(stmt)]
        _index_cache.clear()
        _index_cache[key] = KeywordIndex.build(rows)
    return _index_cache[key]


# ---------- 순위 합치기 · 조항별 묶기 ----------


def fuse(*rankings: Sequence[int], rrf_k: int = RRF_K) -> list[int]:
    """여러 순위 목록을 RRF 로 합칩니다. 두 검색 모두 위에 있는 조각이 가장 앞에 옵니다."""
    score: dict[int, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            score[chunk_id] = score.get(chunk_id, 0.0) + 1 / (rrf_k + rank)
    return sorted(score, key=lambda cid: score[cid], reverse=True)


def diversify(hits: Sequence[Hit], k: int, per_article: int = PER_ARTICLE) -> list[Hit]:
    """같은 (규정, 조항) 조각은 per_article 개까지만 남기고 상위 k 개를 고릅니다."""
    picked, seen = [], Counter()
    for h in hits:
        key = (h.document.title, h.chunk.article)
        if seen[key] >= per_article:
            continue
        seen[key] += 1
        picked.append(h)
        if len(picked) == k:
            break
    return picked


# ---------- 검색 ----------


def search(
    db: Session,
    query: str,
    *,
    k: int | None = None,
    audience: str | None = None,
    chunk_types: Sequence[str] = DEFAULT_TYPES,
) -> list[Hit]:
    k = k or settings.rag_top_k
    expanded = expand(query)
    qv = embed_query(expanded)
    distance = Chunk.embedding.cosine_distance(qv).label("distance")

    base = (
        select(Chunk, Document, distance)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.is_current.is_(True), Chunk.embedding.is_not(None))
        .where(Chunk.chunk_type.in_(chunk_types))
    )
    if audience:  # 직원은 직원용+공통, 관리자는 관리자용+공통
        base = base.where(Document.audience.in_([AUDIENCE_ALL, audience]))

    by_id: dict[int, Hit] = {}
    for c, d, dist in db.execute(base.order_by(distance).limit(CANDIDATES)):
        by_id[c.id] = Hit(chunk=c, document=d, score=1.0 - float(dist))
    vector_ranking = list(by_id)

    keyword_ranking = _keyword_index(db, audience, chunk_types).search(expanded, CANDIDATES)
    missing = [cid for cid in keyword_ranking if cid not in by_id]
    if missing:
        for c, d, dist in db.execute(base.where(Chunk.id.in_(missing))):
            by_id[c.id] = Hit(chunk=c, document=d, score=1.0 - float(dist))

    ranked = [by_id[cid] for cid in fuse(vector_ranking, keyword_ranking) if cid in by_id]
    return diversify(ranked, k)
