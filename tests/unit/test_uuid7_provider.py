"""UUIDv7 provider contract (PO 14.1 / 14.4A)."""

from __future__ import annotations

import concurrent.futures
import uuid

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


def test_new_uuid7_returns_stdlib_uuid_version_7() -> None:
    value = new_uuid7()
    assert type(value) is uuid.UUID
    assert value.version == 7


def test_new_uuid7_unique_under_threads() -> None:
    def _gen(_: int) -> uuid.UUID:
        return new_uuid7()

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(_gen, range(200)))
    assert len(values) == len(set(values))
