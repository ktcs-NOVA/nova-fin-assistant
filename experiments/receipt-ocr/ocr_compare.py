"""OCR 방식 vs 현재 방식(GPT 가 사진을 직접 읽음) 비교 실험 — 2026-11-13.

"OCR API 를 쓰면 AI 없이 되지 않을까?" 를 숫자로 확인하려고 같은 11장·같은 채점 기준으로 세 가지를 잽니다.

  A. vision     현재 방식. 사진을 gpt-4o-mini 에 보냄 (backend app/domains/receipt/service.py 그대로)
  B. ocr-rules  OCR 로 글자만 뽑고, 정규식·키워드 규칙으로 가맹점·날짜·시각·합계·카드 뒷자리를 찾음 (LLM 없음)
  C. ocr-llm    OCR 글자를 gpt-4o-mini 에 "글"로 보내 값을 뽑음 (사진은 밖으로 안 나감, 글은 마스킹 후 전송)

OCR 엔진은 macOS 내장 Vision (기기 안에서 동작, 키·비용 없음). 클라우드 OCR API(네이버 클로바 등)는 키가 없어 재지 못했고,
글자 인식 자체는 비슷하거나 더 나을 수 있지만 "글자 → 필드" 단계(B 의 규칙 또는 C 의 LLM)는 똑같이 필요합니다.

    cd backend
    uv run --with pyobjc-framework-Vision python ../experiments/receipt-ocr/ocr_compare.py            # 세 방식 모두
    uv run --with pyobjc-framework-Vision python ../experiments/receipt-ocr/ocr_compare.py --arms ocr-rules
    uv run --with pyobjc-framework-Vision python ../experiments/receipt-ocr/ocr_compare.py --dump     # OCR 글자만 저장

OCR 글자는 results/ocr_text/ 에 저장됩니다 (원본 영수증의 카드번호 등이 들어 있어 git 에 올라가지 않는 폴더).
A·C 는 실제 OpenAI 호출이라 비용이 듭니다 (11장 gpt-4o-mini 기준 수십 원).
"""

import argparse
import base64
import csv
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))

RECEIPTS = HERE / "receipts"
TRUTH = HERE / "ground_truth.csv"
OCR_DIR = HERE / "results" / "ocr_text"
MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


# ---------------------------------------------------------------------------
# OCR (macOS Vision)
# ---------------------------------------------------------------------------
def ocr_lines(path: Path) -> list[str]:
    """사진 → 줄 단위 글자. 위에서 아래로, 같은 높이는 왼쪽에서 오른쪽으로 이어 붙입니다."""
    import Vision
    from Foundation import NSURL

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_(["ko-KR", "en-US"])
    request.setUsesLanguageCorrection_(True)
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(NSURL.fileURLWithPath_(str(path)), None)
    ok, err = handler.performRequests_error_([request], None)
    if not ok:
        raise RuntimeError(f"OCR 실패: {err}")
    boxes = []
    for obs in request.results() or []:
        cand = obs.topCandidates_(1)
        if not cand:
            continue
        bb = obs.boundingBox()  # 왼쪽 아래가 원점, 0~1
        boxes.append((1 - (bb.origin.y + bb.size.height / 2), bb.origin.x, bb.size.height, str(cand[0].string())))
    boxes.sort()
    lines, cur, cur_y, cur_h = [], [], None, 0
    for y, x, h, text in boxes:
        if cur and abs(y - cur_y) > max(cur_h, h) * 0.6:
            lines.append(" ".join(t for _, t in sorted(cur)))
            cur = []
        if not cur:
            cur_y, cur_h = y, h
        cur.append((x, text))
    if cur:
        lines.append(" ".join(t for _, t in sorted(cur)))
    return lines


def ocr_text(path: Path, *, fresh: bool = False) -> tuple[str, float]:
    """OCR 글자와 걸린 시간(초). 한 번 뽑은 글자는 results/ocr_text 에 두고 다시 씁니다."""
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    cache = OCR_DIR / (path.name + ".txt")
    if cache.exists() and not fresh:
        return cache.read_text(encoding="utf-8"), 0.0
    t0 = time.time()
    text = "\n".join(ocr_lines(path))
    cache.write_text(text, encoding="utf-8")
    return text, time.time() - t0


# ---------------------------------------------------------------------------
# B. 규칙으로 값 찾기 (LLM 없음)
# ---------------------------------------------------------------------------
AMOUNT = r"\d{1,3}(?:[,.]\d{3})+|\d{3,7}"
TOTAL_WORDS = ["결제금액", "받을금액", "받은금액", "합계금액", "승인금액", "거래금액", "판매금액", "총액", "합계", "합 계", "TOTAL", "Total", "금액"]
NOT_MERCHANT = re.compile(r"영수증|매출전표|신용카드|고객용|사업자|대표|전화|TEL|주소|승인|카드|일시|날짜|No\.|POS|\d{3}-\d{2}-\d{5}")
MERCHANT_LABEL = re.compile(r"(?:상\s*호|가맹점명?|매장명?|판매자)\s*[:：]?\s*(.+)")
PURPOSE_WORDS = [
    ("식비", ["커피", "카페", "coffee", "cafe", "식당", "음식", "베이커리", "빵", "편의점", "아메리카노", "라떼", "순두부", "스토어", "곳간"]),
    ("주유비", ["주유", "휘발유", "경유"]),
    ("교통비", ["택시", "철도", "고속버스", "KTX"]),
    ("숙박비", ["호텔", "모텔", "숙박"]),
    ("도서비", ["서점", "도서"]),
    ("소모품비", ["문구", "사무용품", "샵", "shop"]),
]


def _to_int(s: str) -> int:
    return int(re.sub(r"[^\d]", "", s))


def parse_rules(text: str) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = {"merchant": None, "date": None, "time": None, "total_amount": None, "card_last4": None, "purpose_candidates": []}

    # 날짜: 2026-11-01 / 2026.11.01 / 2026년 11월 1일 / 26-11-01
    m = re.search(r"(20\d{2})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})", text)
    if m:
        out["date"] = f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}"
    else:
        m = re.search(r"(?<!\d)(\d{2})[-./](\d{2})[-./](\d{2})(?!\d)", text)
        if m:
            out["date"] = f"20{m[1]}-{m[2]}-{m[3]}"

    # 시각: 처음 나오는 HH:MM (오후면 +12)
    m = re.search(r"(오전|오후|AM|PM)?\s*(?<!\d)(\d{1,2})\s*:\s*(\d{2})(?:\s*:\s*\d{2})?", text)
    if m and int(m[2]) < 24 and int(m[3]) < 60:
        hour = int(m[2])
        if m[1] in ("오후", "PM") and hour < 12:
            hour += 12
        out["time"] = f"{hour:02d}:{m[3]}"

    # 합계: 키워드가 있는 줄(없으면 다음 줄)의 마지막 금액. 키워드 우선순위대로
    for word in TOTAL_WORDS:
        for i, ln in enumerate(lines):
            if word not in ln:
                continue
            nums = re.findall(AMOUNT, ln.split(word, 1)[1]) or (re.findall(AMOUNT, lines[i + 1]) if i + 1 < len(lines) else [])
            nums = [n for n in nums if 100 <= _to_int(n) <= 9_999_999]
            if nums:
                out["total_amount"] = _to_int(nums[-1])
                break
        if out["total_amount"]:
            break

    # 카드 뒷 4자리: 별표로 가린 카드번호에서 별표 뒤에 남은 숫자 4자리 (백엔드 _clean 과 같은 기준)
    for m in re.finditer(r"[\d*]{4}[- ]?[\d*]{2,4}[- ]?[\d*]{2,4}[- ]?[\d*]{3,4}", text):
        raw = m[0]
        if "*" in raw:
            digits = re.sub(r"[^\d]", "", raw.rsplit("*", 1)[-1])
            if len(digits) >= 4:
                out["card_last4"] = digits[-4:]
                break

    # 가맹점: "상호:" 같은 표지가 있으면 그 값, 없으면 맨 위쪽에서 한글이 있는 첫 줄
    for ln in lines:
        m = MERCHANT_LABEL.search(ln)
        if m and re.search(r"[가-힣A-Za-z]", m[1]):
            out["merchant"] = m[1].strip()
            break
    if not out["merchant"]:
        for ln in lines[:8]:
            if re.search(r"[가-힣]{2,}", ln) and not NOT_MERCHANT.search(ln):
                out["merchant"] = ln
                break

    # 용도: 글자에 들어 있는 단어로만 추정 (없으면 기타)
    low = text.lower()
    out["purpose_candidates"] = [p for p, words in PURPOSE_WORDS if any(w.lower() in low for w in words)][:3] or ["기타"]
    return out


# ---------------------------------------------------------------------------
# C. OCR 글자를 LLM 에 글로 보내기
# ---------------------------------------------------------------------------
def parse_llm(text: str) -> dict:
    from app.ai import llm
    from app.ai.masking import mask
    from app.core.config import settings
    from app.domains.receipt import service

    system = service.SYSTEM.replace("사진에서 값을 읽어", "영수증을 OCR 로 뽑은 글자에서 값을 찾아").replace("사진에 없는 값", "글자에 없는 값")
    resp = llm._client().chat.completions.create(
        model=settings.receipt_model,
        messages=[
            {"role": "system", "content": system},
            # 카드번호·전화·사업자번호는 가린 뒤 보냅니다. 카드 뒷자리는 그래서 규칙(parse_rules)으로 따로 찾습니다.
            {"role": "user", "content": "아래는 영수증 OCR 결과입니다 (줄 순서는 위→아래). 지시문의 JSON 형식으로만 답하세요.\n\n" + mask(text)},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    data = json.loads(resp.choices[0].message.content or "{}")
    data.pop("card_number", None)
    out = service._clean(data)
    out["card_last4"] = parse_rules(text)["card_last4"]
    return out


# ---------------------------------------------------------------------------
# A. 현재 방식
# ---------------------------------------------------------------------------
def parse_vision(path: Path) -> dict:
    from app.domains.receipt import service
    from app.domains.receipt.schemas import ReceiptRequest

    req = ReceiptRequest(filename=path.name, media_type=MEDIA[path.suffix.lower()],
                         image_base64=base64.standard_b64encode(path.read_bytes()).decode("ascii"))
    return service.recognize(req)


# ---------------------------------------------------------------------------
# 채점 (backend/scripts/eval_receipt.py 와 같은 기준)
# ---------------------------------------------------------------------------
def score(rows: list[tuple[dict, dict | None]]):
    from scripts.eval_receipt import FIELDS

    hits = {k: 0 for k in [*FIELDS, "purpose"]}
    misses = []
    for t, r in rows:
        if r is None:
            misses.append(f"{t['file']}: 인식 실패")
            continue
        for k, same in FIELDS.items():
            if t.get(k, "") == "":
                if k == "card_last4" and r.get(k):
                    misses.append(f"{t['file']}: card_last4  정답 (가려짐) → 결과 {r.get(k)!r}")
                else:
                    hits[k] += 1
            elif same(r.get(k), t[k]):
                hits[k] += 1
            else:
                misses.append(f"{t['file']}: {k}  정답 {t[k]!r} → 결과 {r.get(k)!r}")
        if not t.get("purpose") or t["purpose"] in (r.get("purpose_candidates") or []):
            hits["purpose"] += 1
        else:
            misses.append(f"{t['file']}: purpose  정답 {t['purpose']!r} → 후보 {r.get('purpose_candidates')}")
    return hits, misses


ARMS = ["vision", "ocr-rules", "ocr-llm"]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", nargs="+", choices=ARMS, default=ARMS)
    ap.add_argument("--dump", action="store_true", help="OCR 글자만 뽑아 저장하고 끝")
    ap.add_argument("--fresh", action="store_true", help="저장된 OCR 글자를 쓰지 않고 다시 뽑음")
    args = ap.parse_args()

    with TRUTH.open(encoding="utf-8-sig") as f:
        truth = list(csv.DictReader(f))

    texts, ocr_secs = {}, []
    if args.dump or any(a.startswith("ocr") for a in args.arms):
        for t in truth:
            texts[t["file"]], sec = ocr_text(RECEIPTS / t["file"], fresh=args.fresh or args.dump)
            if sec:
                ocr_secs.append(sec)
        if ocr_secs:
            print(f"OCR {len(ocr_secs)}장, 평균 {sum(ocr_secs) / len(ocr_secs):.1f}초/장 → {OCR_DIR}")
    if args.dump:
        return

    report = {}
    for arm in args.arms:
        rows, secs = [], []
        for t in truth:
            t0 = time.time()
            try:
                if arm == "vision":
                    r = parse_vision(RECEIPTS / t["file"])
                elif arm == "ocr-rules":
                    r = parse_rules(texts[t["file"]])
                else:
                    r = parse_llm(texts[t["file"]])
            except Exception as e:  # 한 장이 실패해도 나머지는 계속
                print(f"  [{arm}] {t['file']}: 실패 ({type(e).__name__}: {e})")
                r = None
            secs.append(time.time() - t0)
            rows.append((t, r))
        hits, misses = score(rows)
        report[arm] = (hits, misses, sum(secs) / len(secs), len(truth))

    fields = list(next(iter(report.values()))[0])
    print(f"\n{'필드':<14}" + "".join(f"{a:>12}" for a in report))
    for k in fields:
        print(f"{k:<14}" + "".join(f"{report[a][0][k]:>9}/{report[a][3]}" for a in report))
    print(f"{'전체':<14}" + "".join(f"{sum(report[a][0].values()) / (report[a][3] * len(fields)) * 100:>11.0f}%" for a in report))
    print(f"{'초/장(추출)':<12}" + "".join(f"{report[a][2]:>12.1f}" for a in report))
    for a in report:
        print(f"\n[{a}] 틀린 항목 {len(report[a][1])}개")
        for m in report[a][1]:
            print(" -", m)


if __name__ == "__main__":
    main()
