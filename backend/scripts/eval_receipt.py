"""영수증 인식 정답률 측정 (U-06). 실제 OpenAI 호출이라 비용이 듭니다 (11장 기준 gpt-4o 약 100원).

    uv run python -m scripts.eval_receipt                    # settings.receipt_model 로
    uv run python -m scripts.eval_receipt --model gpt-4o-mini
    uv run python -m scripts.eval_receipt --limit 3

사진: experiments/receipt-ocr/receipts/  정답지: experiments/receipt-ocr/ground_truth.csv
채점 기준은 experiments/receipt-ocr/extract_receipts.py 의 eval 과 같습니다
(가맹점은 정답이 결과에 포함되면 정답, 정답지가 비어 있는 칸은 채점 제외, 용도는 후보 안에 있으면 정답).
"""

import argparse
import base64
import csv
import re
import sys
import time
from pathlib import Path

from app.core.config import settings
from app.core.errors import AppError
from app.domains.receipt import service
from app.domains.receipt.schemas import ReceiptRequest

ROOT = Path(__file__).resolve().parents[2]
RECEIPTS = ROOT / "experiments" / "receipt-ocr" / "receipts"
TRUTH = ROOT / "experiments" / "receipt-ocr" / "ground_truth.csv"
MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def norm_text(s) -> str:
    return re.sub(r"\s+", "", str(s or "")).lower()


def norm_int(s) -> str:
    return re.sub(r"[^\d]", "", str(s or ""))


FIELDS = {
    "merchant": lambda got, want: norm_text(got) == norm_text(want) or (norm_text(want) and norm_text(want) in norm_text(got)),
    "date": lambda got, want: (got or "") == (want or ""),
    "time": lambda got, want: (got or "") == (want or ""),
    "total_amount": lambda got, want: norm_int(got) == norm_int(want),
    "card_last4": lambda got, want: norm_int(got) == norm_int(want),
}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", help="기본: settings.receipt_model")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    if args.model:
        settings.receipt_model = args.model
    if settings.ai_mock:
        sys.exit("OPENAI_API_KEY 가 없어 측정할 수 없습니다 (backend/.env).")

    with TRUTH.open(encoding="utf-8-sig") as f:
        truth = list(csv.DictReader(f))
    if args.limit:
        truth = truth[: args.limit]

    hits = {k: 0 for k in [*FIELDS, "purpose"]}
    misses, secs, n = [], [], 0
    print(f"모델 {settings.receipt_model} · {len(truth)}장\n")
    for t in truth:
        path = RECEIPTS / t["file"]
        req = ReceiptRequest(filename=path.name, media_type=MEDIA[path.suffix.lower()],
                             image_base64=base64.standard_b64encode(path.read_bytes()).decode("ascii"))
        t0 = time.time()
        try:
            r = service.recognize(req)
        except AppError as e:
            print(f"  {t['file']}: 실패 ({e.message})")
            misses.append(f"{t['file']}: 인식 실패")
            n += 1
            continue
        secs.append(time.time() - t0)
        n += 1
        line = []
        for k, same in FIELDS.items():
            if t.get(k, "") == "":
                hits[k] += 1  # 정답지가 비어 있으면 채점 제외
                # 단, 가려진 카드번호를 읽어 냈다고 하면 틀린 것으로 본다
                if k == "card_last4" and r.get(k):
                    hits[k] -= 1
                    misses.append(f"{t['file']}: card_last4  정답 (가려짐) → 결과 {r.get(k)!r}")
                continue
            if same(r.get(k), t[k]):
                hits[k] += 1
            else:
                misses.append(f"{t['file']}: {k}  정답 {t[k]!r} → 결과 {r.get(k)!r}")
                line.append(k)
        if t.get("purpose"):
            if t["purpose"] in (r.get("purpose_candidates") or []):
                hits["purpose"] += 1
            else:
                misses.append(f"{t['file']}: purpose  정답 {t['purpose']!r} → 후보 {r.get('purpose_candidates')}")
                line.append("purpose")
        else:
            hits["purpose"] += 1
        print(f"  {t['file']:<28} {secs[-1]:4.1f}s  {r.get('confidence'):<6} {'OK' if not line else '틀림: ' + ', '.join(line)}")

    print(f"\n{'필드':<14}{'정답':>7}{'정답률':>8}")
    for k, v in hits.items():
        print(f"{k:<14}{v:>4}/{n:<3}{v / n * 100:>6.0f}%")
    total = sum(hits.values())
    print(f"{'전체':<14}{total:>4}/{n * len(hits):<3}{total / (n * len(hits)) * 100:>6.0f}%")
    if secs:
        print(f"평균 {sum(secs) / len(secs):.1f}초/장")
    if misses:
        print("\n틀린 항목")
        for m in misses:
            print(" -", m)


if __name__ == "__main__":
    main()
