"""Application-level UUIDv7 provider (clauses 45–46; M1-01 PO resolution 14.1/14.4A)."""

from __future__ import annotations

import threading
import uuid

import uuid6

_uuid7_lock = threading.Lock()


def new_uuid7() -> uuid.UUID:
    """Return a standard-library uuid.UUID with version 7.

    uuid6.uuid7() is not thread-safe; all generation is serialized by a
    module-private lock. The library subclass is normalized to uuid.UUID.
    """
    with _uuid7_lock:
        generated = uuid6.uuid7()
        return uuid.UUID(int=generated.int)
