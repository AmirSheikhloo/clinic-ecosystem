"""Deterministic UUID and National-ID helpers for the demo dataset."""

from __future__ import annotations

import hashlib
import uuid
from uuid import UUID

from clinic_ecosystem.domain.identity.national_id import is_valid_national_id_checksum

DEMO_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def demo_uuid(seed: int, kind: str, index: int) -> UUID:
    """Stable UUIDv5 derived from seed + kind + index (deterministic, not UUIDv7)."""
    return uuid.uuid5(DEMO_NAMESPACE, f"demo:{seed}:{kind}:{index}")


def synthetic_national_id(seed: int, index: int) -> str:
    """Produce a syntactically valid IR National ID (checksum OK, not a real person)."""
    # Mix seed+index into 9 body digits; never all-identical.
    digest = hashlib.sha256(f"nid:{seed}:{index}".encode()).hexdigest()
    body_int = int(digest[:12], 16) % 900_000_000 + 100_000_000
    body = f"{body_int:09d}"
    if body == body[0] * 9:
        body = "123456789"
    total = sum(int(body[i]) * (10 - i) for i in range(9))
    rem = total % 11
    check = rem if rem < 2 else 11 - rem
    value = f"{body}{check}"
    assert is_valid_national_id_checksum(value)
    return value


def synthetic_mobile(seed: int, index: int) -> str:
    """Iran E.164 mobile (+989…) deterministic from seed/index."""
    digest = hashlib.sha256(f"phone:{seed}:{index}".encode()).hexdigest()
    subscriber = int(digest[:8], 16) % 10_000_0000
    return f"+989{subscriber:09d}"
