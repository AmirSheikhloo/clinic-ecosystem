"""Argon2id password hashing helpers for user_accounts.password_hash_argon2id."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password must be non-empty")
    return _HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return True only when the password matches. Never raises for mismatches."""
    try:
        return _HASHER.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
