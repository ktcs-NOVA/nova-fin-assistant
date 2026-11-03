"""에러 응답 형식 통일 — docs/API.md 4번: HTTP 상태코드 + {"error": "사람이 읽을 수 있는 설명"}

서비스 코드에서는 이렇게 던지면 됩니다:

    from app.core.errors import AppError
    raise AppError("items가 비어 있습니다.")              # 400
    raise AppError("제출 건을 찾을 수 없습니다.", 404)
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("nova")


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "요청 형식이 올바르지 않습니다."
    first = errors[0]
    msg = str(first.get("msg", "")).removeprefix("Value error, ")
    if first.get("type") == "value_error":  # 우리가 직접 쓴 한국어 메시지
        return msg
    loc = ".".join(str(x) for x in first.get("loc", ()) if x not in ("body", "query"))
    return f"{loc}: {msg}" if loc else msg


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return error_response(exc.status_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        # FastAPI 기본값은 422 이지만, API.md 약속에 맞춰 400 으로 돌려줍니다.
        return error_response(400, _validation_message(exc))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        detail = exc.detail
        message = detail["error"] if isinstance(detail, dict) and "error" in detail else str(detail)
        return error_response(exc.status_code, str(message))

    # 예상하지 못한 에러도 {"error"} 형식으로. (CORS 미들웨어 안쪽에서 처리돼야
    # 브라우저가 CORS 에러 대신 이 메시지를 볼 수 있으므로, main.py 에서 CORS 보다 먼저 등록)
    @app.middleware("http")
    async def _catch_all(request: Request, call_next):
        try:
            return await call_next(request)
        except OperationalError:
            log.exception("DB 연결 오류")
            return error_response(
                503,
                "DB에 연결할 수 없습니다. backend 폴더에서 'docker compose up -d' 로 DB를 켰는지 확인해 주세요.",
            )
        except Exception:
            log.exception("처리되지 않은 오류: %s %s", request.method, request.url.path)
            return error_response(500, "서버 내부 오류가 발생했습니다.")
