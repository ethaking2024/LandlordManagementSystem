from __future__ import annotations


class LMSError(Exception):
    """Base exception for all LMS application errors."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__


class ConfigurationError(LMSError):
    """Raised when configuration is invalid or missing."""


class DatabaseError(LMSError):
    """Raised when a database operation fails."""


class RepositoryError(LMSError):
    """Raised when a repository operation fails."""


class ValidationError(LMSError):
    """Raised when input validation fails."""


class NotFoundError(LMSError):
    """Raised when a requested resource is not found."""


class ConflictError(LMSError):
    """Raised when a resource conflict occurs (e.g., duplicate, overlap)."""


class BusinessRuleError(LMSError):
    """Raised when a business rule is violated."""


class ApplicationError(LMSError):
    """Raised when an application service operation fails."""
