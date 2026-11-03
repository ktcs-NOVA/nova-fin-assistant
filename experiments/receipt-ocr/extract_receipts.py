"""
영수증 인식 단독 테스트 (U-06 영수증 자동 정리)

  python extract_receipts.py extract         receipts/ 의 사진을 모두 읽어 results/<파일명>.json 저장
  python extract_receipts.py extract --limit 2   처음 2장만 (비용 확인용)
  python extract_receipts.py eval            results/*.json 과 ground_truth.csv 를 비교해 필드별 정답률 출력

뽑는 값: 가맹점, 업종, 날짜, 시각, 합계 금액, 카드 뒷 4자리, 승인번호, 품목, 용도 후보
기능명세서 U-06 의 출력(가맹점·금액·일시·용도 후보)이 평가의 주축이고, 나머지는 U-04 검증용 보조 값입니다.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import re
import sys
import time
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

HERE = Path(__file__).parent
RECEIPTS = HERE / "receipts"
RESULTS = HERE / "results"
TRUTH = HERE / "ground_truth.csv"

MODEL = "claude-opus-5-5"
MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

# 용도 후보는 이 목록 안에서만 고르게 함 (U-07 계정과목 제안과 이어지는 값)
PURPOSES = ["식비", "회의비", "교통비", "숙박비", "주유비", "소모품비", "도서비", "경조사비", "기타"]


# ---------- 출력 형식 (Claude 가 이 모양으로만 답하도록 강제) ----------

class Item(BaseModel):
    name: str = Field(description="품목명, 영수증에 적힌 그대로")
    amount: int | None = Field(description="품목 금액(원). 없으면 null")


class Receipt(BaseModel):
    merchant: str | None = Field(description="가맹점(상호)명. 못 읽으면 null")
    business_type: str | None = Field(description="업종 추정. 예: 음식점, 카페, 편의점, 주유소, 숙박, 택시, 서점")
    date: str | None = Field(description="결제 날짜 YYYY-MM-DD. 못 읽으면 null")
    time: str | None = Field(description="결제 시각 HH:MM (24시간). 못 읽으면 null")
    total_amount: int | None = Field(description="최종 결제(합계) 금액, 원 단위 정수. 못 읽으면 null")
    card_last4: str | None = Field(description="카드번호 마지막 4자리. 마스킹되어 없으면 null")
    approval_no: str | None = Field(description="승인번호. 없으면 null")
    items: list[Item] = Field(description="품목 목록. 없으면 빈 배열")
    purpose_candidates: list[Literal[tuple(PURPOSES)]] = Field(  # type: ignore[valid-type]
        description="이 지출의 용도로 가능한 후보, 가능성 높은 순. 1~3개"
    )
    confidence: Literal["high", "medium", "low"] = Field(description="전체 판독 신뢰도")
    notes: str | None = Field(description="흐림·잘림·추정한 부분 등 사람이 확인해야 할 메모. 없으면 null")


PROMPT = f"""이 사진은 한국 영수증(카드 매출전표 또는 간이 영수증)입니다.
아래 값을 읽어 주세요. 사진에 없는 값은 지어내지 말고 null 로 두세요.

- 날짜는 YYYY-MM-DD, 시각은 24시간 HH:MM 으로 통일합니다. (예: 2026.10.20 / 26-10-20 → 2026-10-20, 오후 7:35 → 19:35)
- 금액은 쉼표와 '원'을 빼고 정수로 적습니다. 합계는 최종 결제 금액(할인·포인트 적용 후)입니다.
- 카드번호는 마지막 4자리만 적습니다. 별표(*)로 가려져 있으면 null.
- 용도 후보는 다음 중에서만 고릅니다: {", ".join(PURPOSES)}
- 숫자 0 과 영문 O, 1 과 l 처럼 헷갈리는 부분, 흐려서 추정한 부분은 notes 에 적어 주세요.
"""


def load_env() -> None:
    """experiments/receipt-ocr/.env 의 KEY=VALUE 를 환경변수로 (python-dotenv 없이)."""
    import os
    env = HERE / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def image_files() -> list[Path]:
    return sorted(p for p in RECEIPTS.iterdir() if p.suffix.lower() in MEDIA)


# ---------- extract ----------

def extract_one(client: anthropic.Anthropic, path: Path) -> dict:
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    t0 = time.time()
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": MEDIA[path.suffix.lower()], "data": data}},
                {"type": "text", "text": PROMPT},
            ],
        }],
        output_format=Receipt,
    )
    elapsed = round(time.time() - t0, 1)
    if response.stop_reason == "refusal":
        return {"file": path.name, "error": "refusal", "stop_details": str(response.stop_details)}
    parsed: Receipt = response.parsed_output
    return {
        "file": path.name,
        **parsed.model_dump(),
        "_meta": {
            "model": MODEL,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "seconds": elapsed,
        },
    }


def cmd_extract(limit: int | None) -> None:
    load_env()
    files = image_files()
    if not files:
        sys.exit(f"receipts/ 에 사진이 없습니다. jpg/png/webp 를 넣어 주세요: {RECEIPTS}")
    if limit:
        files = files[:limit]
    client = anthropic.Anthropic()
    RESULTS.mkdir(exist_ok=True)
    rows = []
    for i, path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {path.name} ...", end=" ", flush=True)
        try:
            result = extract_one(client, path)
        except anthropic.AuthenticationError:
            sys.exit("\nAPI 키가 없거나 잘못되었습니다. .env 의 ANTHROPIC_API_KEY 를 확인해 주세요.")
        except anthropic.RateLimitError as e:
            wait = int(e.response.headers.get("retry-after", "30"))
            print(f"속도 제한. {wait}초 후 다시 시도")
            time.sleep(wait)
            result = extract_one(client, path)
        except anthropic.APIStatusError as e:
            result = {"file": path.name, "error": f"HTTP {e.status_code}: {e.message}"}
        except anthropic.APIConnectionError:
            sys.exit("\n네트워크 오류. 인터넷 연결을 확인해 주세요.")

        (RESULTS / f"{path.stem}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        if "error" in result:
            print(f"실패: {result['error']}")
        else:
            m = result["_meta"]
            print(f"{result['merchant']} | {result['date']} {result['time']} | {result['total_amount']}원 "
                  f"| {result['purpose_candidates']} | {result['confidence']} ({m['seconds']}s, in {m['input_tokens']} / out {m['output_tokens']} tok)")
        rows.append(result)

    # 한눈에 보는 표
    with (RESULTS / "summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["file", "merchant", "business_type", "date", "time", "total_amount", "card_last4",
                    "approval_no", "purpose_candidates", "confidence", "notes", "error"])
        for r in rows:
            w.writerow([r.get("file"), r.get("merchant"), r.get("business_type"), r.get("date"), r.get("time"),
                        r.get("total_amount"), r.get("card_last4"), r.get("approval_no"),
                        " / ".join(r.get("purpose_candidates", []) or []), r.get("confidence"), r.get("notes"), r.get("error")])
    total_in = sum(r.get("_meta", {}).get("input_tokens", 0) for r in rows)
    total_out = sum(r.get("_meta", {}).get("output_tokens", 0) for r in rows)
    print(f"\n완료: {len(rows)}장 → results/summary.csv  (입력 {total_in} tok, 출력 {total_out} tok)")


# ---------- eval ----------

def norm_text(s: str | None) -> str:
    return re.sub(r"\s+", "", (s or "")).lower()


def norm_int(s) -> str:
    return re.sub(r"[^\d]", "", str(s or ""))


FIELDS = {
    "merchant": lambda a, b: norm_text(a) == norm_text(b) or (norm_text(b) and norm_text(b) in norm_text(a)),
    "date": lambda a, b: (a or "") == (b or ""),
    "time": lambda a, b: (a or "") == (b or ""),
    "total_amount": lambda a, b: norm_int(a) == norm_int(b),
    "card_last4": lambda a, b: norm_int(a) == norm_int(b),
}


def cmd_eval() -> None:
    if not TRUTH.exists():
        sys.exit(f"정답지가 없습니다: {TRUTH}")
    with TRUTH.open(encoding="utf-8-sig") as f:
        truth = {row["file"]: row for row in csv.DictReader(f)}
    if not truth:
        sys.exit("ground_truth.csv 에 데이터 행이 없습니다. README 의 작성법을 참고하세요.")

    hits = {k: 0 for k in list(FIELDS) + ["purpose"]}
    n = 0
    misses: list[str] = []
    for fname, t in truth.items():
        rpath = RESULTS / f"{Path(fname).stem}.json"
        if not rpath.exists():
            misses.append(f"{fname}: 결과 없음 (extract 먼저)")
            continue
        r = json.loads(rpath.read_text(encoding="utf-8"))
        if "error" in r:
            misses.append(f"{fname}: 추출 실패 ({r['error']})")
            n += 1
            continue
        n += 1
        for k, same in FIELDS.items():
            if t.get(k, "") == "":        # 정답지에 비어 있으면 채점 제외
                hits[k] += 1
                continue
            if same(r.get(k), t[k]):
                hits[k] += 1
            else:
                misses.append(f"{fname}: {k}  정답 {t[k]!r} → 결과 {r.get(k)!r}")
        if t.get("purpose", ""):
            if t["purpose"] in (r.get("purpose_candidates") or []):
                hits["purpose"] += 1
            else:
                misses.append(f"{fname}: purpose  정답 {t['purpose']!r} → 후보 {r.get('purpose_candidates')}")
        else:
            hits["purpose"] += 1

    if n == 0:
        sys.exit("채점할 결과가 없습니다.")
    print(f"영수증 {n}장 기준 필드별 정답률\n")
    print(f"{'필드':<14}{'정답':>6}{'정답률':>8}")
    for k, v in hits.items():
        print(f"{k:<14}{v:>4}/{n:<3}{v / n * 100:>6.0f}%")
    if misses:
        print("\n틀린 항목")
        for m in misses:
            print(" -", m)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract", help="영수증 사진에서 값 추출")
    e.add_argument("--limit", type=int, help="처음 N장만 처리")
    sub.add_parser("eval", help="정답지와 비교해 정답률 출력")
    args = ap.parse_args()
    if args.cmd == "extract":
        cmd_extract(args.limit)
    else:
        cmd_eval()
