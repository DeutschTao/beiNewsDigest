"""Custom exceptions and FastAPI exception handlers."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    code: int = 500
    message: str = "Internal error"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)
        if message:
            self.message = message


class NotFoundError(AppError):
    code = 404
    message = "Not found"


class SourceExistsError(AppError):
    code = 400
    message = "Source already exists"


class SourceLimitError(AppError):
    code = 400
    message = "Source limit reached"


class RSSParseError(AppError):
    code = 400
    message = "Invalid or unreachable URL"


class FetchError(AppError):
    code = 502
    message = "Failed to fetch from upstream"


def _payload(code: int, message: str, data=None):
    return {"code": code, "message": message, "data": data}


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return JSONResponse(status_code=200, content=_payload(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        msg = f"Validation error: {exc.errors()[0].get('msg', 'invalid request')}"
        return JSONResponse(status_code=200, content=_payload(400, msg))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        from .logger import logger
        logger.exception(f"Unhandled error: {exc}")
        return JSONResponse(status_code=200, content=_payload(500, "Internal server error"))