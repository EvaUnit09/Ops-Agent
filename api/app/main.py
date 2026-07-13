from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import assets, checkouts, health, users
from app.schemas import ApiError, ApiResponse, ResponseMeta

app = FastAPI(
    title=get_settings().app_name,
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(assets.router)
app.include_router(checkouts.router)
app.include_router(users.router)


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    envelope = ApiResponse[dict[str, object]](
        data=None,
        error=ApiError(code=code, message=message),
        meta=ResponseMeta(count=0, limit=None),
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(envelope),
    )


@app.exception_handler(HTTPException)
def handle_http_exception(
    request: Request,
    exception: HTTPException,
) -> JSONResponse:
    del request
    message = exception.detail if isinstance(exception.detail, str) else "request failed"
    return error_response(
        status_code=exception.status_code,
        code=f"http_{exception.status_code}",
        message=message,
    )


@app.exception_handler(RequestValidationError)
def handle_validation_exception(
    request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    del request, exception
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        message="request parameters are invalid",
    )


@app.exception_handler(Exception)
def handle_unexpected_exception(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    del request, exception
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="an unexpected error occurred",
    )
