"""검색: 질문과 가까운 조각을 찾습니다. 의미 검색 + 키워드 검색을 섞은 하이브리드 검색.

1. 일상어 사전으로 검색어 보강 (법카 → 법인카드, 회의비 → 업무추진비)
2. 의미 검색 (pgvector 코사인 거리) 후보 + 키워드 검색 (낱말을 글자 2개씩 자른 BM25) 후보
3. 두 순위를 RRF(순위 역수 합)로 합침 — "노래방", "23시"처럼 단어가 맞아야 하는 질문 대응
   키워드 쪽 비중은 KEYWORD_WEIGHT(0.5) — 처음 보는 표현의 질문에서 1위를 뺏지 않도록
4. 같은 조항에서 나온 조각은 최대 2개까지만 — 전결표 별표 조각(700여 개)이 결과를 독점하지 않도록
5. 결과 조항이 「다른 규정」에 따른다고 하면 그 문장 + 질문으로 그 규정 안에서 다시 찾아 바로 뒤에 넣음
   (업무추진비 지침 제9조 "사용시간은 「법인카드 관리 및 사용 지침」에 따른다" → 법인카드 지침 제10조)
6. 결과 조항이 "별표 1에 따라"처럼 표를 가리키면 그 별표를 바로 뒤에 덧붙임 (금액이 별표에 있으므로)
   이 조각은 상위 k 개 밖에 추가로 붙습니다.

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
# 키워드 순위의 비중 (의미 검색은 1). 1 이면 기존 평가셋(82문항) 상위 5 적중 95.1% 지만
# 처음 보는 질문(qa_holdout.csv 18문항)은 72.2% 로 떨어짐. 0.5 는 93.9% / 77.8% 로 균형 (2026-11-19)
KEYWORD_WEIGHT = 0.5
MAX_REFERENCES = 2  # 다른 규정을 따르라는 조항을 따라가 덧붙일 최대 조각 수
MAX_APPENDICES = 2  # 조항이 가리키는 별표를 덧붙일 최대 별표 수

# 별표 1에 따라 / 별표 3의2 → '1', '3의2'
_APPENDIX_MENTION = re.compile(r"별표\s*(\d+(?:의\d+)?)")

# 「법인카드 관리 및 사용 지침」에 따른다 / 을 준용한다
_ARTICLE_HEAD = re.compile(r"^\s*제\d+조(?:의\d+)?\([^)]*\)|^\s*[①-⑳]")
_REFERENCE = re.compile(r"「([^」]+)」(?:에\s*따른다|을\s*준용|를\s*준용)")

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


def fuse(
    *rankings: Sequence[int], weights: Sequence[float] | None = None, rrf_k: int = RRF_K
) -> list[int]:
    """여러 순위 목록을 RRF 로 합칩니다. 두 검색 모두 위에 있는 조각이 가장 앞에 옵니다.

    weights 를 주면 순위 목록마다 비중을 다르게 줍니다 (기본은 모두 1).
    """
    weights = weights or [1.0] * len(rankings)
    score: dict[int, float] = {}
    for ranking, weight in zip(rankings, weights, strict=True):
        for rank, chunk_id in enumerate(ranking, start=1):
            score[chunk_id] = score.get(chunk_id, 0.0) + weight / (rrf_k + rank)
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


def _hybrid(
    db: Session,
    text: str,
    *,
    audience: str | None,
    chunk_types: Sequence[str],
    title: str | None = None,
) -> list[Hit]:
    """의미 검색 + 키워드 검색 후보를 RRF 로 합친 순위. title 을 주면 그 규정 안에서만."""
    qv = embed_query(text)
    distance = Chunk.embedding.cosine_distance(qv).label("distance")
    base = (
        select(Chunk, Document, distance)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.is_current.is_(True), Chunk.embedding.is_not(None))
        .where(Chunk.chunk_type.in_(chunk_types))
    )
    if audience:  # 직원은 직원용+공통, 관리자는 관리자용+공통
        base = base.where(Document.audience.in_([AUDIENCE_ALL, audience]))
    if title:
        base = base.where(Document.title == title)

    by_id: dict[int, Hit] = {}
    for c, d, dist in db.execute(base.order_by(distance).limit(CANDIDATES)):
        by_id[c.id] = Hit(chunk=c, document=d, score=1.0 - float(dist))
    vector_ranking = list(by_id)

    index = _keyword_index(db, audience, chunk_types)
    keyword_ranking = index.search(text, len(index.ids) if title else CANDIDATES)
    missing = [cid for cid in keyword_ranking if cid not in by_id]
    if missing:  # 키워드로만 찾은 조각도 코사인 점수를 붙임 (title 밖의 조각은 여기서 걸러짐)
        for c, d, dist in db.execute(base.where(Chunk.id.in_(missing))):
            by_id[c.id] = Hit(chunk=c, document=d, score=1.0 - float(dist))

    ranking = fuse(vector_ranking, keyword_ranking, weights=[1.0, KEYWORD_WEIGHT])
    return [by_id[cid] for cid in ranking if cid in by_id]


def references(content: str) -> list[tuple[str, str]]:
    """조항 본문에서 「규정명」에 따른다 / 준용한다 로 가리키는 (규정명, 그 문장)."""
    found: dict[str, str] = {}
    for line in content.splitlines():
        sentence = _ARTICLE_HEAD.sub("", line).strip()  # '제9조(기타)' 같은 머리는 검색에 방해
        for title in _REFERENCE.findall(line):
            found.setdefault(title, sentence)
    return list(found.items())


def without_title_words(text: str, title: str) -> str:
    """질문에서 원래 규정명의 낱말(업무추진비는 → 빼기)을 지웁니다.

    참조된 규정 안에서 다시 찾을 때 원래 규정명이 남아 있으면,
    그 이름을 언급만 하는 조항(예: 법인카드 지침 제5조 사용범위)이 앞서기 때문입니다.
    """
    names = [w for w in title.split() if len(w) >= 2 and w not in {"및", "규정", "지침"}]
    return " ".join(w for w in text.split() if not any(w.startswith(n) for n in names))


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
    hits = diversify(_hybrid(db, expanded, audience=audience, chunk_types=chunk_types), k)

    # 결과 조항이 「다른 규정」을 따르라고 하면, 질문 + 그 문장으로 그 규정 안에서 다시 찾아 바로 뒤에 넣음
    out, have, added = list(hits), {h.chunk.id for h in hits}, 0
    for h in hits:
        for title, sentence in references(h.chunk.content):
            if title == h.document.title or added >= MAX_REFERENCES:
                continue
            found = _hybrid(
                db,
                f"{without_title_words(expanded, h.document.title)} {sentence}",
                audience=audience,
                chunk_types=chunk_types,
                title=title,
            )
            if found and found[0].chunk.id not in have:
                out.insert(out.index(h) + 1, found[0])
                have.add(found[0].chunk.id)
                added += 1
    return follow_appendices(db, out[:k], expanded, audience, chunk_types)


def appendix_labels(content: str) -> list[str]:
    """조항 본문이 가리키는 별표 이름 ('별표 1에 따라' → '별표 1'). 전결표 '<별표>' 처럼 번호 없는 건 제외."""
    return list(dict.fromkeys(f"별표 {n}" for n in _APPENDIX_MENTION.findall(content)))


def follow_appendices(
    db: Session,
    hits: list[Hit],
    query: str,
    audience: str | None,
    chunk_types: Sequence[str],
) -> list[Hit]:
    """조항이 '별표 1에 따라'처럼 표를 가리키면, 그 별표를 조항 바로 뒤에 덧붙입니다.

    금액·한도는 대부분 별표에 있는데, 질문과 비슷한 건 조항 쪽이라 별표가 검색에서 빠지곤 합니다.
    그러면 답변이 숫자 없이 "별표를 확인하세요"로 끝나므로 표를 함께 넘깁니다.
    덧붙인 조각의 점수는 가리킨 조항의 점수를 따릅니다 (그 조항이 근거로 쓰일 때만 의미가 있으므로).
    """
    out = list(hits)
    present = {(h.document.id, h.chunk.article) for h in hits}
    added = 0
    # 질문의 주제 규정(1위 조항의 규정)에서만 따라감. 회식 질문에 4위로 섞인 여비규정 식비 조항이
    # 출장 여비표를 끌고 와서 "회식비 1인당 3만 원" 같은 엉뚱한 답이 나온 적이 있음
    topic = hits[0].document.id if hits else None
    for h in hits:
        if h.document.id != topic:
            continue
        for label in appendix_labels(h.chunk.content):
            if added >= MAX_APPENDICES or (h.document.id, label) in present:
                continue
            chunks = db.scalars(
                select(Chunk)
                .where(Chunk.document_id == h.document.id, Chunk.article == label)
                .where(Chunk.chunk_type.in_(chunk_types))
                .order_by(Chunk.seq)
            ).all()
            if not chunks:
                continue
            if len(chunks) > PER_ARTICLE:  # 긴 별표는 질문과 키워드가 가장 맞는 묶음만
                order = _keyword_index(db, audience, chunk_types).search(query, len(chunks) * 50)
                rank = {cid: i for i, cid in enumerate(order)}
                chunks = sorted(chunks, key=lambda c: rank.get(c.id, len(rank)))[:PER_ARTICLE]
            pos = out.index(h) + 1
            for c in chunks:
                out.insert(pos, Hit(chunk=c, document=h.document, score=h.score))
                pos += 1
            present.add((h.document.id, label))
            added += 1
    return out
