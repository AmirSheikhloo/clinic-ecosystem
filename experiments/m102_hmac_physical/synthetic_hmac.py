"""Synthetic domain-separated digests for disposable experiments.

These are NOT production HMAC keys, KMS material, or clause-767 vectors.
They only produce deterministic 32-byte blind-index stand-ins for uniqueness
and dual-write tests under ephemeral PG15.
"""

from __future__ import annotations

import hashlib
from uuid import UUID


def synthetic_lookup_hmac(
    *,
    tenant_id: UUID,
    id_type: str,
    issuing_country_or_authority: str,
    normalized_identifier: str,
    hmac_key_version: int,
) -> bytes:
    """Deterministic 32-byte stand-in keyed by synthetic generation version."""
    canonical = (
        f"{str(tenant_id).lower().strip()}"
        f"|{id_type.upper().strip()}"
        f"|{issuing_country_or_authority.upper().strip()}"
        f"|{normalized_identifier}"
    )
    material = f"m102-exp|v{hmac_key_version}|{canonical}".encode("utf-8")
    return hashlib.sha256(material).digest()
