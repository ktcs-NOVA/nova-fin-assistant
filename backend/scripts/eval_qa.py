"""U-01 규정 Q&A 평가 — 정답 조항을 얼마나 잘 찾고, 근거 없는 질문을 잘 거르는지 숫자로 확인합니다.

    uv run python -m scripts.eval_qa                    # 검색 + 답변 생성까지
    uv run python -m scripts.eval_qa --retrieval-only   # 검색만 (빠르고 비용 거의 없음)
    uv run python -m scripts.eval_qa --k 10             # 상위 몇 개까지 볼지

평가 질문: data/eval/qa_eval.csv  (expected 칸에 '규정명 조항', 여러 개면 ; 로 구분, 비우면 근거 없음 질문)
결과 저장: data/eval/results/qa_YYYYMMDD_HHMM.csv  (엑셀로 바로 열림)

지표
- 1위 적중  : 정답 조항이 검색 1위
- 상위 k 적중: 정답 조항 중 하나라도 상위 k 안에 있음
- 모두 찾음 : 정답이 여러 개(종합 질문)일 때 전부 상위 k 안에 있음
- 근거 판단 : 근거 있는 질문은 답변, 근거 없는 질문은 "담당자 확인 필요"로 거른 비율
"""

import argparse
import csv
import sys
import time
from collections import defaultdict
from datetime import datetime

from app.core.config import BACKEND_DIR, settings
from app.core.db import SessionLocal
from app.rag import answerer, retriever

EVAL_FILE = BACKEND_DIR / "data" / "eval" / "qa_eval.csv"
RESULT_DIR = BACKEND_DIR / "data" / "eval" / "results"


def label(hit: retriever.Hit) -> str:
    return f"{hit.document.title} {hit.chunk.article or ''}".strip()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="U-01 규정 Q&A 평가")
    parser.add_argument("--k", type=int, default=5, help="상위 몇 개까지 볼지 (기본 5)")
    parser.add_argument("--retrieval-only", action="store_true", help="답변 생성 없이 검색만 평가")
    args = parser.parse_args()

    if settings.ai_mock:
        print("⚠ OPENAI_API_KEY 가 없어 목업 모드입니다. 점수가 의미 없습니다.\n")

    with open(EVAL_FILE, encoding="utf-8-sig", newline="") as f:
        cases = list(csv.DictReader(f))

    rows, by_cat = [], defaultdict(list)
    with SessionLocal() as db:
        for case in cases:
            expected = [e.strip() for e in case["expected"].split(";") if e.strip()]
            started = time.perf_counter()
            hits = retriever.search(db, case["question"], k=args.k)
            labels = [label(h) for h in hits]

            ranks = [labels.index(e) + 1 for e in expected if e in labels]
            row = {
                "id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "expected": "; ".join(expected) or "(근거 없음)",
                "top1": labels[0] if labels else "",
                "top1_score": round(hits[0].score, 3) if hits else "",
                f"top{args.k}": " | ".join(f"{lb} ({h.score:.2f})" for lb, h in zip(labels, hits)),
                "rank": min(ranks) if ranks else "",
                "hit1": int(bool(ranks) and min(ranks) == 1) if expected else "",
                "hitk": int(bool(ranks)) if expected else "",
                "all_found": int(len(ranks) == len(expected)) if len(expected) > 1 else "",
            }

            if not args.retrieval_only:
                result = answerer.answer(db, case["question"])
                cited = [f"{s['regulation']} {s['article']}" for s in result.sources]
                row["grounded"] = int(result.grounded)
                # 근거 있는 질문은 답변해야 정답, 근거 없는 질문은 걸러야 정답
                row["ground_ok"] = int(result.grounded == bool(expected))
                row["cited"] = " | ".join(cited)
                row["cited_ok"] = int(any(e in cited for e in expected)) if expected else ""
                row["answer"] = result.answer.replace("\n", " ")
            row["seconds"] = round(time.perf_counter() - started, 2)

            rows.append(row)
            by_cat[case["category"]].append(row)
            mark = {1: "✅", 0: "❌"}.get(row["hitk"], "—") if expected else "—"
            print(f"{mark} [{row['category']}] {row['question'][:30]:<30} → {row['top1']} ({row['top1_score']})")

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULT_DIR / f"qa_{datetime.now():%Y%m%d_%H%M}.csv"
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def pct(vals: list) -> str:
        vals = [v for v in vals if v != ""]
        return f"{sum(vals) / len(vals) * 100:5.1f}% ({sum(vals)}/{len(vals)})" if vals else "    -"

    print(f"\n===== 결과 요약 (상위 {args.k}) =====")
    header = f"{'구분':<8}{'1위 적중':>16}{f'상위{args.k} 적중':>16}{'모두 찾음':>16}"
    if not args.retrieval_only:
        header += f"{'근거 판단':>16}{'출처 일치':>16}"
    print(header)
    for cat, items in [*by_cat.items(), ("전체", rows)]:
        line = f"{cat:<8}{pct([r['hit1'] for r in items]):>16}{pct([r['hitk'] for r in items]):>16}"
        line += f"{pct([r['all_found'] for r in items]):>16}"
        if not args.retrieval_only:
            line += f"{pct([r['ground_ok'] for r in items]):>16}{pct([r['cited_ok'] for r in items]):>16}"
        print(line)
    print(f"\n평균 소요 시간: {sum(r['seconds'] for r in rows) / len(rows):.2f}초 / 질문")

    misses = [r for r in rows if r["hitk"] == 0]
    if misses:
        print(f"\n----- 상위 {args.k} 안에서 못 찾은 질문 -----")
        for r in misses:
            print(f"[{r['id']}] {r['question']}\n    정답: {r['expected']}\n    검색: {r[f'top{args.k}']}")
    print(f"\n자세한 결과: {out}")


if __name__ == "__main__":
    main()
