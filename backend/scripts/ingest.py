"""규정 문서를 벡터 DB 에 적재합니다.

    uv run python -m scripts.ingest                       # data/regulations 폴더 전체
    uv run python -m scripts.ingest 파일1.hwp 파일2.hwpx    # 특정 파일만
    uv run python -m scripts.ingest --audience admin 회계규정.hwp   # 관리자 전용 문서
    uv run python -m scripts.ingest --force               # 내용이 같아도 다시 적재

내용이 바뀌지 않은 문서는 자동으로 건너뜁니다 (임베딩 비용 절약).
"""

import argparse
import sys
from pathlib import Path

from app.core.config import BACKEND_DIR, settings
from app.core.db import SessionLocal
from app.rag.ingest import ingest_file
from app.rag.loader import SUPPORTED

DEFAULT_DIR = BACKEND_DIR / "data" / "regulations"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔 한글 깨짐 방지

    parser = argparse.ArgumentParser(description="규정 문서 적재")
    parser.add_argument(
        "paths", nargs="*", type=Path, help="적재할 파일 (생략하면 data/regulations 전체)"
    )
    parser.add_argument("--audience", default="all", choices=["all", "employee", "admin"])
    parser.add_argument("--force", action="store_true", help="내용이 같아도 다시 적재")
    args = parser.parse_args()

    paths = args.paths or sorted(p for p in DEFAULT_DIR.iterdir() if p.suffix.lower() in SUPPORTED)
    if not paths:
        print(f"적재할 파일이 없습니다: {DEFAULT_DIR}")
        return

    if settings.ai_mock:
        print("⚠ OPENAI_API_KEY 가 없어 목업 임베딩으로 적재합니다 (의미 검색은 되지 않음).\n")

    with SessionLocal() as db:
        for path in paths:
            try:
                r = ingest_file(db, path, audience=args.audience, force=args.force)
                print(
                    f"[{r.status:8}] {r.title}  ({r.chunks}개 조각)"
                    if r.chunks
                    else f"[{r.status:8}] {r.title}"
                )
            except Exception as e:
                db.rollback()
                print(f"[실패    ] {path.name}: {e}")


if __name__ == "__main__":
    main()
