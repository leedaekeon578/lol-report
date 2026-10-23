from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """브라우저로 나가는 오류. 문구는 고정이며 원문 예외나 Riot 응답은 담지 않는다."""

    status_code = 500
    code = "OTHER_ERROR"
    message = "조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."

    def __init__(self, status_code: int | None = None) -> None:
        super().__init__(self.code)
        if status_code is not None:
            self.status_code = status_code


class InvalidInput(AppError):
    status_code = 400
    code = "INVALID_INPUT"
    message = "닉네임#태그 형식으로 입력해 주세요."


class AccountNotFound(AppError):
    status_code = 404
    code = "ACCOUNT_NOT_FOUND"
    message = "해당 닉네임#태그의 계정을 찾을 수 없습니다."


class RateLimited(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    message = "Riot API 호출 한도를 넘어 조회를 멈췄습니다. 잠시 후 다시 시도해 주세요."


class KeyExpired(AppError):
    status_code = 502
    code = "KEY_EXPIRED"
    message = "Riot API 키가 만료되었거나 유효하지 않습니다. 서버 키를 갱신해야 합니다."


class OtherError(AppError):
    """그 밖의 오류. Riot 쪽 실패는 502, 서버 내부 문제는 500으로 쓴다."""

    status_code = 502


def error_response(error: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message}},
    )


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
        return error_response(error)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        # 기본 422 응답은 입력값을 되돌려 주므로 고정 문구로 바꾼다.
        return error_response(InvalidInput())

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, error: Exception) -> JSONResponse:
        return error_response(OtherError(status_code=500))
