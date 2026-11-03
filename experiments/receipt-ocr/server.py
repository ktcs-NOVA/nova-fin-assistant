"""
영수증 인식 테스트 서버 (U-06) — 프론트 "영수증 등록" 화면을 실제 API 로 돌려보기 위한 임시 서버

  .venv/bin/python server.py            http://localhost:8000 에서 대기
  .venv/bin/python server.py --port 8001

제공하는 주소 (나머지 /api/* 는 백엔드 담당이 만듭니다)

  POST /api/verify   (backend/precheck 가 저장소에 있을 때만) PM 이 만든 U-04 판정 엔진을 그대로 호출
  POST /api/receipt
    보내는 것: { "filename": "a.jpg", "media_type": "image/jpeg", "image_base64": "..." }
    받는 것:   extract_receipts.py 의 Receipt 와 같은 모양 (merchant, date, time, total_amount, ... notes)
    실패:      { "error": "설명" } 과 400 / 500

프론트에서 쓰려면 frontend/.env.local 에  VITE_USE_MOCK=false  를 적고 dev 서버를 다시 켭니다.
API 키는 이 폴더의 .env (ANTHROPIC_API_KEY) 에서 읽습니다. 키는 브라우저로 나가지 않습니다.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import anthropic

from extract_receipts import MEDIA, extract_bytes, load_env

# PM 의 U-04 판정 엔진(backend/precheck)이 저장소에 있으면 /api/verify 도 제공
BACKEND = Path(__file__).resolve().parents[2] / "backend"
verify_claim = None
if (BACKEND / "precheck").is_dir():
    sys.path.insert(0, str(BACKEND))
    try:
        from precheck import verify_claim  # noqa: E402
    except Exception as e:  # 엔진 쪽 오류는 서버를 못 켜게 하지 않음
        print(f"precheck 엔진을 불러오지 못했습니다: {e}")

ALLOWED_MEDIA = set(MEDIA.values())
MAX_BYTES = 10 * 1024 * 1024  # 사진 10MB 제한
ORIGIN = "http://localhost:5173"  # Vite dev 서버 (CORS 허용 대상)

client: anthropic.Anthropic | None = None


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", ORIGIN)
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:  # CORS 사전 요청
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/api/health":
            eps = ["POST /api/receipt"] + (["POST /api/verify"] if verify_claim else [])
            self._send(200, {"ok": True, "endpoints": eps})
        else:
            self._send(404, {"error": "이 테스트 서버는 POST /api/receipt 만 제공합니다. 다른 기능은 백엔드 서버가 필요합니다."})

    def do_POST(self) -> None:
        if self.path not in ("/api/receipt", "/api/verify"):
            self._send(404, {"error": "이 테스트 서버는 POST /api/receipt (와 /api/verify) 만 제공합니다. 다른 기능은 백엔드 서버가 필요합니다."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "요청 본문이 JSON 이 아닙니다."})
            return

        if self.path == "/api/verify":
            if verify_claim is None:
                self._send(404, {"error": "판정 엔진(backend/precheck)이 이 저장소에 없습니다. PM 브랜치를 합친 뒤 다시 켜 주세요."})
                return
            try:
                result = verify_claim(body)
            except ValueError as e:
                self._send(400, {"error": str(e)})
                return
            except Exception as e:
                self._send(500, {"error": f"판정 중 오류: {e}"})
                return
            print(f"[verify] {body.get('trip_type')} / {len(body.get('items', []))}건 → {result.get('overall')}")
            self._send(200, result)
            return

        media_type = body.get("media_type")
        if media_type not in ALLOWED_MEDIA:
            self._send(400, {"error": f"지원하지 않는 사진 형식입니다: {media_type}. jpg/png/webp 만 됩니다."})
            return
        try:
            image = base64.standard_b64decode(body.get("image_base64") or "")
        except ValueError:
            self._send(400, {"error": "image_base64 를 해독할 수 없습니다."})
            return
        if not image:
            self._send(400, {"error": "사진 데이터가 비어 있습니다."})
            return
        if len(image) > MAX_BYTES:
            self._send(400, {"error": "사진이 10MB 를 넘습니다. 줄여서 다시 올려 주세요."})
            return

        name = body.get("filename", "?")
        print(f"[receipt] {name} ({len(image) // 1024} KB) ...", end=" ", flush=True)
        try:
            result = extract_bytes(client, image, media_type)
        except anthropic.AuthenticationError:
            print("키 오류")
            self._send(500, {"error": "API 키가 없거나 잘못되었습니다. experiments/receipt-ocr/.env 를 확인해 주세요."})
            return
        except anthropic.RateLimitError:
            print("속도 제한")
            self._send(429, {"error": "API 호출이 너무 잦습니다. 잠시 후 다시 시도해 주세요."})
            return
        except anthropic.APIStatusError as e:
            print(f"HTTP {e.status_code}")
            self._send(502, {"error": f"인식 API 오류 (HTTP {e.status_code}): {e.message}"})
            return
        except anthropic.APIConnectionError:
            print("네트워크 오류")
            self._send(502, {"error": "인식 API 에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요."})
            return

        if "error" in result:
            print("거부됨")
            self._send(422, {"error": "이 사진은 인식이 거부되었습니다. 영수증 사진이 맞는지 확인해 주세요."})
            return

        meta = result.pop("_meta")
        print(f"{result.get('merchant')} | {result.get('total_amount')}원 | {result.get('confidence')} "
              f"({meta['seconds']}s, in {meta['input_tokens']} / out {meta['output_tokens']} tok)")
        self._send(200, result)

    def log_message(self, *_args) -> None:  # 기본 접속 로그는 끔 (위 print 로 충분)
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    load_env()
    client = anthropic.Anthropic()
    print(f"영수증 인식 테스트 서버: http://localhost:{args.port}  (POST /api/receipt, 허용 출처 {ORIGIN})")
    print("끝내려면 Ctrl+C")
    try:
        ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n종료")
