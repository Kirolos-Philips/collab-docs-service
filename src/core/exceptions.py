"""
Custom exceptions for the application.

Provides structured error handling with HTTP status codes.
"""

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base exception for application errors."""

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An unexpected error occurred",
    ):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(AppException):
    """Resource not found error."""

    def __init__(self, resource: str = "Resource", identifier: str | None = None):
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} with id '{identifier}' not found"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(AppException):
    """Resource conflict error (e.g., duplicate entry)."""

    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ValidationError(AppException):
    """Validation error."""

    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class UnauthorizedError(AppException):
    """Authentication required error."""

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenError(AppException):
    """Permission denied error."""

    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class DatabaseError(AppException):
    """Database operation error."""

    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )
