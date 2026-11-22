"""AES-256-GCM phone field protection, frozen specification clauses 768-770.

This module deliberately does NOT implement durable nonce allocation, KMS access,
database persistence, or permission checks. They are required host-service ports.
Phone AAD tokens remain explicit until formally frozen by the Product Owner.
"""
from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from clinic_ecosystem.shared_kernel.pii_contracts import aad_v1, require_e164


@dataclass(frozen=True)
class EncryptionKey:
    """Secret supplied by an authenticated KMS/key-provider boundary."""
    version: int
    material: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.version) is not int or not 1 <= self.version <= 32767:
            raise ValueError("encryption key version must be a positive SMALLINT")
        if type(self.material) is not bytes or len(self.material) != 32:
            raise ValueError("AES-256-GCM requires exactly 32 key bytes")


@dataclass(frozen=True)
class FieldContext:
    """Person owner must remain the ORIGINAL immutable owner after merges."""
    tenant_id: uuid.UUID
    original_person_id: uuid.UUID
    record_id: uuid.UUID
    field_type: str
    issuing_authority: str

    def __post_init__(self) -> None:
        # Validate complete context up front; not a user-selected decryption AAD.
        self.aad_bytes()

    def aad_bytes(self) -> bytes:
        return aad_v1(
            tenant_id=self.tenant_id,
            original_person_id=self.original_person_id,
            record_id=self.record_id,
            id_type_or_field_type=self.field_type,
            issuing_country_or_authority=self.issuing_authority,
        )


@dataclass(frozen=True)
class EncryptedPhone:
    """Persistence-compatible columns for person_phones; never a plaintext DTO."""
    phone_ciphertext: bytes = field(repr=False)
    nonce_96bit: bytes = field(repr=False)
    auth_tag_128bit: bytes = field(repr=False)
    encryption_key_version: int
    aad_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.phone_ciphertext, bytes) or not self.phone_ciphertext:
            raise ValueError("ciphertext must be nonempty bytes")
        if not isinstance(self.nonce_96bit, bytes) or len(self.nonce_96bit) != 12:
            raise ValueError("GCM nonce must be exactly 96 bits")
        if not isinstance(self.auth_tag_128bit, bytes) or len(self.auth_tag_128bit) != 16:
            raise ValueError("GCM authentication tag must be exactly 128 bits")
        if type(self.encryption_key_version) is not int or not 1 <= self.encryption_key_version <= 32767:
            raise ValueError("invalid encryption key version")
        if self.aad_version != 1:
            raise ValueError("unsupported AAD version: fail closed")


class DurableNonceReservation(Protocol):
    def reserve(self, *, key_version: int, nonce_96bit: bytes) -> None:
        """Atomically and durably reject any nonce previously used by this key.

        Implementations MUST namespace versions by immutable KMS key identity,
        never recycle a version, survive worker restarts, and make reservations
        durable before a ciphertext could be stored. In-memory sets are NOT a
        production implementation.
        """


def encrypt_phone(
    *,
    phone_e164: str,
    context: FieldContext,
    key: EncryptionKey,
    nonce_reservation: DurableNonceReservation,
) -> EncryptedPhone:
    """Encrypt a normalized phone with fresh random nonce + durable reservation.

    No default production nonce ledger: absent/untrusted adapter fails closed.
    Callers separately persist returned fields and any derived keyed HMAC in a
    single application transaction with verified tenant/RLS boundaries.
    """
    canonical = require_e164(phone_e164)
    if not isinstance(context, FieldContext) or not isinstance(key, EncryptionKey):
        raise TypeError("trusted context and encryption key objects are required")
    reserve = getattr(nonce_reservation, "reserve", None)
    if not callable(reserve):
        raise TypeError("durable nonce reservation is mandatory")
    nonce = secrets.token_bytes(12)
    reserve(key_version=key.version, nonce_96bit=nonce)
    sealed = AESGCM(key.material).encrypt(
        nonce, canonical.encode("ascii"), context.aad_bytes()
    )
    return EncryptedPhone(
        phone_ciphertext=sealed[:-16],
        nonce_96bit=nonce,
        auth_tag_128bit=sealed[-16:],
        encryption_key_version=key.version,
        aad_version=1,
    )


def decrypt_phone(
    *, encrypted: EncryptedPhone, context: FieldContext, key: EncryptionKey
) -> str:
    """Decrypt only with reconstructed trusted record AAD, never caller AAD.

    Cryptographic tampering/context transplants raise InvalidTag. Authorization,
    audit logging, and key retrieval must be enforced by the enclosing service.
    """
    if not isinstance(encrypted, EncryptedPhone):
        raise TypeError("encrypted phone envelope is required")
    if not isinstance(context, FieldContext) or not isinstance(key, EncryptionKey):
        raise TypeError("trusted context and encryption key objects are required")
    if encrypted.encryption_key_version != key.version:
        raise ValueError("encryption key version mismatch")
    plain = AESGCM(key.material).decrypt(
        encrypted.nonce_96bit,
        encrypted.phone_ciphertext + encrypted.auth_tag_128bit,
        context.aad_bytes(),
    )
    return require_e164(plain.decode("ascii"))


def rotate_phone_encryption(
    *,
    encrypted: EncryptedPhone,
    context: FieldContext,
    old_key: EncryptionKey,
    new_key: EncryptionKey,
    nonce_reservation: DurableNonceReservation,
) -> EncryptedPhone:
    """AES rewrap only: caller must separately manage HMAC key rotation."""
    if old_key.version == new_key.version or secrets.compare_digest(
        old_key.material, new_key.material
    ):
        raise ValueError("AES rotation requires a distinct key and key version")
    phone = decrypt_phone(encrypted=encrypted, context=context, key=old_key)
    return encrypt_phone(
        phone_e164=phone,
        context=context,
        key=new_key,
        nonce_reservation=nonce_reservation,
    )
