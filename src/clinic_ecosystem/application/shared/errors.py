"""Typed application errors mapped to RFC 9457 problem responses at the edge."""

from __future__ import annotations


class AppError(Exception):
    status = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, extra: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.extra = extra or {}


class ValidationFailed(AppError):
    status = 400
    code = "validation_error"


class Forbidden(AppError):
    status = 403
    code = "forbidden"


class NotFound(AppError):
    status = 404
    code = "not_found"


class Conflict(AppError):
    status = 409
    code = "conflict"


class PreconditionFailed(AppError):
    status = 412
    code = "precondition_failed"


class PreconditionRequired(AppError):
    status = 428
    code = "precondition_required"


class IdempotencyInProgressError(AppError):
    status = 425
    code = "idempotency_in_progress"


class IdempotencyKeyReuse(AppError):
    status = 409
    code = "idempotency_key_reuse"
