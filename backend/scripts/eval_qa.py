"""U-01 규정 Q&A 평가 — 정답 조항을 얼마나 잘 찾고, 근거 없는 질문을 잘 거르는지 숫자로 확인합니다.

    uv run python -m scripts.eval_qa                    # 검색 + 답변 생성까지
    uv run python -m scripts.eval_qa --retrieval-only   # 검색만 (빠르고 비용 거의 없음)
    uv run python -m scripts.eval_qa --k 10             # 상위 몇 개까지 볼지

평가 질문: data/eval/qa_eval.csv
- expected    : '규정명 조항', 여러 개면 ; 로 구분, 비우면 근거 없음 질문
- group       : 같은 뜻을 다르게 표현한 질문끼리 같은 이름 (호텔비 / 숙박비 / 잠잘 곳 비용)
- must_contain: 답변에 꼭 있어야 할 표현. ; 는 모두, | 는 그중 하나 (예: 청구서;영수증, 3분의 1|1/3)
결과 저장: data/eval/results/qa_YYYYMMDD_HHMM.csv  (엑셀로 바로 열림)

지표
- 1위 적중  : 정답 조항이 검색 1위
- 상위 k 적중: 정답 조항 중 하나라도 상위 k 안에 있음
- 모두 찾음 : 정답이 여러 개(종합 질문)일 때 전부 상위 k 안에 있음
- 근거 판단 : 근거 있는 질문은 답변, 근거 없는 질문은 "담당자 확인 필요"로 거른 비율
- 필수 표현 : 답변에 must_contain 표현이 들어 있는 비율 (조항은 맞는데 금액이 틀린 답변을 잡음)
- 표현 일치 : 그룹의 모든 질문이 같은 정답 조항으로 답한 그룹의 비율
"""

import argparse
import csv
import re
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


def contains_required(answer: str, spec: str) -> bool:
    """must_contain 검사. ; 는 모두, | 는 그중 하나. 띄어쓰기와 천 단위 쉼표는 무시합니다."""

    def squash(text: str) -> str:
        return re.sub(r"[\s,]", "", text)

    target = squash(answer)
    return all(
        any(squash(option) in target for option in part.split("|"))
        for part in spec.split(";")
        if part.strip()
    )


def split_labels(text: str, sep: str) -> set[str]:
    return {x.strip() for x in text.split(sep) if x.strip()}


def group_report(rows: list[dict]) -> list[dict]:
    """같은 뜻의 질문 묶음별로, 표현이 달라도 같은 조항으로 답하는지 봅니다.

    same_top1 : 모든 질문의 검색 1위 조항이 같음
    same_cited: 모든 질문이 인용한 조항 중에 공통된 정답 조항이 있음 (검색만 평가할 때는 "")
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["group"]:
            groups[row["group"]].append(row)

    report = []
    for name, items in groups.items():
        same_cited: int | str = ""
        if all("cited" in r for r in items):
            common = set.intersection(*(split_labels(r["cited"], "|") for r in items))
            expected = set.union(*(split_labels(r["expected"], ";") for r in items))
            same_cited = int(bool(common & expected))
        report.append(
            {
                "group": name,
                "size": len(items),
                "same_top1": int(len({r["top1"] for r in items}) == 1),
                "same_cited": same_cited,
                "items": items,
            }
        )
    return report


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
                "group": case["group"],
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
                must = case["must_contain"]
                row["must_contain"] = must
                row["must_ok"] = int(contains_required(result.answer, must)) if must else ""
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
        header += f"{'근거 판단':>16}{'출처 일치':>16}{'필수 표현':>16}"
    print(header)
    for cat, items in [*by_cat.items(), ("전체", rows)]:
        line = f"{cat:<8}{pct([r['hit1'] for r in items]):>16}{pct([r['hitk'] for r in items]):>16}"
        line += f"{pct([r['all_found'] for r in items]):>16}"
        if not args.retrieval_only:
            line += f"{pct([r['ground_ok'] for r in items]):>16}{pct([r['cited_ok'] for r in items]):>16}"
            line += f"{pct([r['must_ok'] for r in items]):>16}"
        print(line)

    groups = group_report(rows)
    if groups:
        print("\n===== 표현 일치 (같은 뜻, 다른 표현) =====")
        for g in groups:
            cited = {1: "✅", 0: "❌"}.get(g["same_cited"], "—")
            top1 = {1: "✅", 0: "❌"}[g["same_top1"]]
            print(f"{g['group']:<10} 질문 {g['size']}개 | 1위 동일 {top1} | 같은 정답 조항으로 답변 {cited}")
            if g["same_cited"] == 0 or (g["same_cited"] == "" and not g["same_top1"]):
                for r in g["items"]:
                    print(f"    [{r['id']}] {r['question']}\n        → {r.get('cited') or r['top1'] or '(근거 없음)'}")
        print(f"\n1위 동일: {pct([g['same_top1'] for g in groups])}")
        print(f"표현 일치: {pct([g['same_cited'] for g in groups])}")

    print(f"\n평균 소요 시간: {sum(r['seconds'] for r in rows) / len(rows):.2f}초 / 질문")

    misses = [r for r in rows if r["hitk"] == 0]
    if misses:
        print(f"\n----- 상위 {args.k} 안에서 못 찾은 질문 -----")
        for r in misses:
            print(f"[{r['id']}] {r['question']}\n    정답: {r['expected']}\n    검색: {r[f'top{args.k}']}")
    print(f"\n자세한 결과: {out}")


if __name__ == "__main__":
    main()
