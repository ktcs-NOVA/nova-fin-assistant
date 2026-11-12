"""청구 검증 평가 — 평가용 청구 건을 사전검증 엔진에 넣고 기대 판정과 비교합니다.

    python -m scripts.eval_verify            # 요약 + 틀린 건
    python -m scripts.eval_verify -v         # 모든 건을 한 줄씩

평가 데이터: data/eval/verify_eval.json (청구 건마다 요청 + 기대 판정)
- DB·LLM 호출 없이 규칙 엔진(app.precheck)만 돌리므로 바로 실행됩니다.
- 기대값은 규정 조항과 종원 님 FAQ(오류 매핑·검증 사례)에서 정했고, 엔진 출력을 보고 맞추지 않았습니다.
- disputed 가 true 인 건은 자료끼리 기준이 달라 팀이 먼저 정해야 하는 건입니다. 점수에서 빼고 따로 보여 줍니다.

보고서 지표 (중간보고서 6주차 평가 계획과 같은 이름)
- 전체 판정 일치율:   종합 판정(규정상 확인 가능 / 보완 필요 / 담당자 확인 필요)이 기대와 같은 비율
- 오류 탐지율:        기대한 오류 규칙(rule_id)을 엔진이 찾아낸 비율  (놓친 오류 비율 = 1 - 오류 탐지율)
- 판정 단계 일치율:    찾아낸 규칙의 판정이 기대와 같은 비율
- 근거 조항 일치율:    찾아낸 규칙의 근거 조항이 기대 조항을 포함하는 비율
- 정상 건 오탐률:      정상(규정상 확인 가능)이어야 하는 건에 엔진이 경고를 낸 비율
- 담당자 확인 이관율:  담당자 확인으로 넘겨야 할 규칙을 담당자 확인으로 낸 비율
"""

import json
import sys
from collections import defaultdict

from pathlib import Path

from app.precheck import verify_claim

BACKEND_DIR = Path(__file__).resolve().parents[1]
EVAL_FILE = BACKEND_DIR / "data" / "eval" / "verify_eval.json"
OK, FIX, CHECK = "규정상 확인 가능", "보완 필요", "담당자 확인 필요"


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({n / d * 100:.0f}%)" if d else "-"


def run_case(case: dict) -> dict:
    """엔진을 돌려 기대와 비교한 결과를 돌려준다."""
    result = verify_claim(case["request"])
    found = defaultdict(list)  # rule_id -> [(verdict, basis)]
    for it in result["items"]:
        if it.get("rule_id") and it["verdict"] != OK:
            found[it["rule_id"]].append((it["verdict"], it.get("basis", "")))

    exp = case["expect"]
    rule_rows = []
    for rid, (verdict, basis) in exp["rules"].items():
        hits = found.get(rid, [])
        hit = bool(hits)
        verdict_ok = any(v == verdict for v, _ in hits)
        basis_ok = (not basis) or any(basis in b for _, b in hits)
        rule_rows.append({"rule": rid, "expected": verdict, "hit": hit, "verdict_ok": verdict_ok,
                          "basis_ok": basis_ok, "got": [v for v, _ in hits]})
    extra = sorted(set(found) - set(exp["rules"]))
    return {"case": case, "overall": result["overall"], "overall_ok": result["overall"] == exp["overall"],
            "rules": rule_rows, "extra": extra}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    verbose = "-v" in sys.argv
    data = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    rows = [run_case(c) for c in data["cases"]]
    scored = [r for r in rows if not r["case"]["disputed"]]
    disputed = [r for r in rows if r["case"]["disputed"]]

    def line(r: dict) -> str:
        c = r["case"]
        mark = "✅" if r["overall_ok"] and all(x["hit"] and x["verdict_ok"] for x in r["rules"]) and not r["extra"] else "❌"
        return f"{mark} {c['id']:<4} {c['name'][:40]:<40} 기대 {c['expect']['overall']} / 결과 {r['overall']}"

    if verbose:
        for r in rows:
            print(line(r))
        print()

    # ---- 집계 (disputed 제외) ----
    overall_ok = sum(r["overall_ok"] for r in scored)
    exp_rules = [x for r in scored for x in r["rules"]]
    hit = [x for x in exp_rules if x["hit"]]
    verdict_ok = [x for x in hit if x["verdict_ok"]]
    basis_ok = [x for x in hit if x["basis_ok"]]
    clean = [r for r in scored if r["case"]["expect"]["overall"] == OK]
    false_alarm = [r for r in clean if r["overall"] != OK]
    exp_check = [x for x in exp_rules if x["expected"] == CHECK]
    check_ok = [x for x in exp_check if x["hit"] and x["verdict_ok"]]
    over_assert = [x for x in exp_check if x["hit"] and not x["verdict_ok"] and FIX in x["got"]]
    extra_cases = [r for r in scored if r["extra"] and r["case"]["expect"]["overall"] != OK]

    print(f"===== 청구 검증 평가: {len(scored)}건 (기준 확정 필요 {len(disputed)}건은 제외) =====")
    print(f"전체 판정 일치율     {pct(overall_ok, len(scored))}")
    print(f"오류 탐지율          {pct(len(hit), len(exp_rules))}   → 놓친 오류 {len(exp_rules) - len(hit)}개")
    print(f"판정 단계 일치율      {pct(len(verdict_ok), len(hit))}")
    print(f"근거 조항 일치율      {pct(len(basis_ok), len(hit))}")
    print(f"정상 건 오탐률        {pct(len(false_alarm), len(clean))}")
    print(f"담당자 확인 이관율    {pct(len(check_ok), len(exp_check))}   (보완 필요로 단정한 건 {len(over_assert)}개)")
    print(f"기대하지 않은 규칙이 함께 걸린 건  {len(extra_cases)}건")

    print("\n--- 영역별 전체 판정 일치율 ---")
    by_cat = defaultdict(lambda: [0, 0])
    for r in scored:
        by_cat[r["case"]["category"]][1] += 1
        by_cat[r["case"]["category"]][0] += r["overall_ok"]
    for cat, (n, d) in by_cat.items():
        print(f"{cat:<8} {pct(n, d)}")

    bad = [r for r in scored if not (r["overall_ok"] and all(x["hit"] and x["verdict_ok"] and x["basis_ok"] for x in r["rules"]) and not r["extra"])]
    if bad:
        print("\n--- 기대와 다른 건 ---")
    for r in bad:
        c = r["case"]
        print(f"[{c['id']}] {c['name']}  (출처: {c['source']})")
        print(f"    종합: 기대 {c['expect']['overall']} / 결과 {r['overall']}")
        for x in r["rules"]:
            if not (x["hit"] and x["verdict_ok"] and x["basis_ok"]):
                why = "못 찾음" if not x["hit"] else ("판정 다름: " + ",".join(x["got"]) if not x["verdict_ok"] else "근거 조항 다름")
                print(f"    {x['rule']}: 기대 {x['expected']} → {why}")
        if r["extra"]:
            print(f"    기대하지 않은 규칙: {', '.join(r['extra'])}")

    # ---- 종원 님 오류 유형(오류 매핑 M01~M21)별 커버리지 ----
    by_map = defaultdict(list)
    for r in rows:
        for m in r["case"].get("mapping", []):
            by_map[m].append(r)
    if by_map:
        print("\n--- 종원 님 오류 유형별 확인 (평가 건이 있는 유형만) ---")
        for m in sorted(by_map, key=lambda x: (x.startswith("TC"), x)):
            rs = by_map[m]
            good = sum(1 for r in rs if r["overall_ok"] and all(x["hit"] and x["verdict_ok"] for x in r["rules"]))
            state = "엔진이 처리" if good == len(rs) else ("일부만 처리" if good else "엔진에 규칙 없음")
            tag = " (기준 확정 필요)" if any(r["case"]["disputed"] for r in rs) else ""
            print(f"{m:<5} {good}/{len(rs)}  {state}{tag}")

    if disputed:
        print("\n--- 기준 확정이 필요한 건 (점수에서 제외) ---")
        for r in disputed:
            c = r["case"]
            print(f"[{c['id']}] {c['name']}  기대 {c['expect']['overall']} / 결과 {r['overall']}")
            print(f"    {c['note']}")


if __name__ == "__main__":
    main()
