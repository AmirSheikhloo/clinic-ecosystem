"""Auth application errors. Messages are intentionally generic at the API boundary."""

from __future__ import annotations


class AuthApplicationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class InvalidCredentials(AuthApplicationError):
    def __init__(self) -> None:
        super().__init__("invalid_credentials", "Invalid credentials")


class AccountUnavailable(AuthApplicationError):
    def __init__(self) -> None:
        # Same outward wording as invalid credentials for login responses.
        super().__init__("invalid_credentials", "Invalid credentials")


class AuthRealmUnavailable(AuthApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "auth_realm_unavailable",
            "Authentication is not available in this environment",
        )


class PermissionDenied(AuthApplicationError):
    def __init__(self) -> None:
        super().__init__("permission_denied", "Permission denied")
