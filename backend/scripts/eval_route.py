"""챗봇 도구 선택 평가 — 질문마다 규정 답변 / 절차 안내 / 되묻기를 맞게 고르는지 확인합니다.

    uv run python -m scripts.eval_route

평가 질문: data/eval/route_eval.csv
- expected: answer / clarify / procedure:업무 이름. 여러 답이 괜찮으면 | 로 구분
도구 선택만 하므로 DB 는 필요 없고, 질문당 LLM 호출 한 번입니다.
"""

import csv
import sys
from collections import Counter

from app.core.config import BACKEND_DIR, settings
from app.domains.qa import assistant

EVAL_FILE = BACKEND_DIR / "data" / "eval" / "route_eval.csv"


def label(route: assistant.Route) -> str:
    return f"procedure:{route.task}" if route.kind == "procedure" else route.kind


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if settings.ai_mock:
        print("⚠ OPENAI_API_KEY 가 없어 단어 규칙으로만 고릅니다.\n")

    with open(EVAL_FILE, encoding="utf-8-sig", newline="") as f:
        cases = list(csv.DictReader(f))

    correct, by_kind, misses = 0, Counter(), []
    for case in cases:
        got = label(assistant.route(case["question"]))
        ok = got in case["expected"].split("|")
        correct += ok
        kind = case["expected"].split("|")[0].split(":")[0]
        by_kind[(kind, ok)] += 1
        print(f"{'✅' if ok else '❌'} {case['question'][:34]:<34} → {got}")
        if not ok:
            misses.append((case, got))

    print(f"\n===== 결과: {correct}/{len(cases)} ({correct / len(cases) * 100:.0f}%) =====")
    for kind in ("procedure", "clarify", "answer"):
        total = by_kind[(kind, True)] + by_kind[(kind, False)]
        if total:
            print(f"{kind:<10} {by_kind[(kind, True)]}/{total}")
    for case, got in misses:
        print(f"[{case['id']}] {case['question']}\n    정답: {case['expected']}  선택: {got}")


if __name__ == "__main__":
    main()
