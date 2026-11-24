from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.logging import logger


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class BadRequestError(AppException):
    def __init__(self, message: str = "Bad request", details: Optional[Any] = None, code: str = "BAD_REQUEST"):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None, code: str = "NOT_FOUND"):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(AppException):
    def __init__(self, message: str = "Resource already exists", details: Optional[Any] = None, code: str = "CONFLICT"):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed", details: Optional[Any] = None, code: str = "UNAUTHENTICATED"):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class PermissionDeniedError(AppException):
    def __init__(self, message: str = "Permission denied", details: Optional[Any] = None, code: str = "FORBIDDEN"):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ValidationError(AppException):
    def __init__(self, message: str = "Validation error", details: Optional[Any] = None, code: str = "VALIDATION_ERROR"):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details=details,
        )


def create_error_response(
    code: str,
    message: str,
    status_code: int,
    details: Optional[Any] = None,
) -> JSONResponse:
    """Builds a standardized error envelope JSONResponse with explicit CORS headers."""
    response = JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
        },
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler for custom application exceptions."""
    logger.warning("Application exception: code=%s, message=%s, path=%s", exc.code, exc.message, request.url.path)
    return create_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handler for standard Starlette/FastAPI HTTPExceptions."""
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_SERVER_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    logger.warning("HTTP exception %d on %s: %s", exc.status_code, request.url.path, exc.detail)
    return create_error_response(
        code=code,
        message=str(exc.detail),
        status_code=exc.status_code,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for Pydantic request validation errors."""
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    formatted_errors = [
        {
            "field": ".".join(str(loc) for loc in err["loc"] if loc != "body"),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]
    return create_error_response(
        code="VALIDATION_ERROR",
        message="Invalid request payload or query parameters",
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        details=formatted_errors,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled 500 exceptions."""
    logger.exception("Unhandled server error processing request %s: %s", request.url.path, str(exc))
    return create_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
