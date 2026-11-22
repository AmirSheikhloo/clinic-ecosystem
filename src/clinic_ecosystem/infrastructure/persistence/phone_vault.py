"""Authenticated transactional PII phone persistence (M1-02, proposed service).

Existing TP0002 person_phones columns + TP0007 FORCE RLS are used verbatim.
Preconditions: configured authoritative JWT/JTI verifier, runtime DB role,
permitted RBAC action, tenant-scoped KMS key, approved phone HMAC provider,
and an authoritative *durable* nonce ledger sharing this transaction.

The nonce-ledger schema and signed phone-HMAC input contract are not present
in the current official tp0001..tp0007 migration lineage. This service MUST
fail closed until those external contracts are provisioned and approved.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID
import secrets

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.authenticated_uow import (
    VerifiedTenantDbSession,
)
from clinic_ecosystem.infrastructure.persistence.permissions import SqlPermissionService
from clinic_ecosystem.shared_kernel.pii_contracts import (
    LookupDigest, require_e164, mask_phone_e164, canonical_aad_tokens,
)
from clinic_ecosystem.shared_kernel.pii_encryption import (
    EncryptionKey, FieldContext, seal_phone_aesgcm,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class NonceReuseRejected(ValueError):
    pass


class PhoneWriteRejected(PermissionError):
    pass


@dataclass(frozen=True)
class TenantPhoneEncryptionKey:
    tenant_id: UUID
    key_identity: UUID   # stable KMS identity; NOT just a key-version integer
    key: EncryptionKey

    def __post_init__(self) -> None:
        if type(self.tenant_id) is not UUID or type(self.key_identity) is not UUID:
            raise ValueError("validated tenant and key identity UUIDs required")
        if self.tenant_id.int == 0 or self.key_identity.int == 0:
            raise ValueError("nil tenant or key identity forbidden")
        if type(self.key) is not EncryptionKey:
            raise TypeError("validated AES encryption key required")


class PhoneHmacProvider(Protocol):
    async def derive(self, *, tenant_id: UUID, phone_e164: str) -> LookupDigest:
        """Use the *approved*, managed keyed phone input contract.

        No built-in defaults because phone HMAC message bytes remain unsigned.
        """


class TenantKeyProvider(Protocol):
    async def phone_aes_key(self, *, tenant_id: UUID) -> TenantPhoneEncryptionKey:
        """Fetch authorized per-tenant KMS material; never return an env hardcode."""


class NonceRegistry(Protocol):
    async def reserve(
        self,
        *,
        tenant_id: UUID,
        aes_key_identity: UUID,
        nonce_96bit: bytes,
    ) -> None:
        """Durable globally unique reservation for immutable AES key identity.

        MUST share this service's AsyncSession transaction and reject duplicates.
        """


class SqlNonceRegistry:
    """Requires a separately approved/preinstalled, FORCE-RLS nonce table.

    Mandatory future physical contract: pii_nonce_reservations(tenant_id,
    aes_key_identity, nonce_96bit, created_at_utc), with a globally enforced
    UNIQUE(aes_key_identity, nonce_96bit), and RLS/privileges. If it does not
    exist, INSERT fails. No official migration is made by this source file.
    """

    _INSERT = text(
        """
        INSERT INTO pii_nonce_reservations
          (tenant_id, aes_key_identity, nonce_96bit, created_at_utc)
        VALUES (:tenant, :key_id, :nonce, :created_at)
        ON CONFLICT (aes_key_identity, nonce_96bit) DO NOTHING
        RETURNING nonce_96bit
        """
    )

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def reserve(
        self, *, tenant_id: UUID, aes_key_identity: UUID, nonce_96bit: bytes
    ) -> None:
        if not isinstance(tenant_id, UUID) or not isinstance(aes_key_identity, UUID):
            raise TypeError("KMS key identity and authenticated tenant UUID required")
        if not isinstance(nonce_96bit, bytes) or len(nonce_96bit) != 12:
            raise ValueError("AES-GCM nonce must be exactly 96 bits")
        result = await self._session.execute(
            self._INSERT,
            {
                "tenant": tenant_id,
                "key_id": aes_key_identity,
                "nonce": nonce_96bit,
                "created_at": datetime.now(timezone.utc),
            },
        )
        if result.scalar_one_or_none() is None:
            raise NonceReuseRejected("AES-GCM nonce reuse for this key is forbidden")


class SqlPhoneVault:
    """Restricted phone create-only vertical slice, with auditable no-PII logs.

    All repository operations run in the caller's verified_jwt_transaction.
    No standalone commit or transaction is allowed. Caller must not expose
    access to arbitrary SQL against the privileged session.
    """

    def __init__(
        self,
        *,
        scope: VerifiedTenantDbSession,
        key_provider: TenantKeyProvider,
        hmac_provider: PhoneHmacProvider,
        nonce_registry: NonceRegistry,
        phone_field_type: str,
        phone_issuing_authority: str,
        create_permission_code: str,
    ) -> None:
        if type(scope) is not VerifiedTenantDbSession:
            raise TypeError("verified tenant DB scope is mandatory")
        if getattr(scope, "_auth", None) is None:
            raise TypeError("verified tenant DB scope is mandatory")
        phone_field_type, phone_issuing_authority = canonical_aad_tokens(
            phone_field_type, phone_issuing_authority
        )
        if not create_permission_code or not create_permission_code.isascii():
            raise ValueError("configured RBAC permission code is mandatory")
        for port, name, action in (
            (key_provider, "key provider", "phone_aes_key"),
            (hmac_provider, "phone HMAC provider", "derive"),
            (nonce_registry, "durable nonce registry", "reserve"),
        ):
            if not callable(getattr(port, action, None)):
                raise TypeError(f"{name} is mandatory")
        # Enforce the actual SQL ledger on the SAME authenticated session.
        # A test-only in-memory ledger, unrelated connection, or no-op
        # reservation must never be accepted by this persistence service.
        if (
            not isinstance(nonce_registry, SqlNonceRegistry)
            or nonce_registry._session is not scope.session
        ):
            raise TypeError("nonce ledger must use the same SQL transaction session")
        self._scope = scope
        self._key_provider = key_provider
        self._hmac_provider = hmac_provider
        self._nonce_registry = nonce_registry
        self._field_type = phone_field_type
        self._authority = phone_issuing_authority
        self._permission = create_permission_code

    async def create(
        self, *, original_owner_person_id: UUID, phone_e164: str,
        is_primary: bool = False, is_shared_phone: bool = False,
    ) -> UUID:
        if not isinstance(original_owner_person_id, UUID):
            raise TypeError("original immutable owner UUID required")
        normalized = require_e164(phone_e164)
        await self._scope.assert_tenant_guc()
        tenant = self._scope.principal.tenant_id
        principal = self._scope.principal.principal_id

        allowed = await SqlPermissionService(self._scope.session).principal_has(
            tenant_id=tenant,
            principal_id=principal,
            permission_code=self._permission,
        )
        if not allowed:
            raise PhoneWriteRejected("phone write permission denied")

        owner = await self._scope.session.scalar(
            text(
                "SELECT id FROM tenant_persons "
                "WHERE tenant_id = :tenant AND id = :owner"
            ),
            {"tenant": tenant, "owner": original_owner_person_id},
        )
        if owner is None:
            raise PhoneWriteRejected("person not found in authenticated tenant")

        key_ref = await self._key_provider.phone_aes_key(tenant_id=tenant)
        if (
            not isinstance(key_ref, TenantPhoneEncryptionKey)
            or key_ref.tenant_id != tenant
            or not isinstance(key_ref.key_identity, UUID)
        ):
            raise PhoneWriteRejected("KMS returned an invalid tenant/key identity")
        lookup = await self._hmac_provider.derive(
            tenant_id=tenant, phone_e164=normalized
        )
        if not isinstance(lookup, LookupDigest):
            raise PhoneWriteRejected("approved keyed phone HMAC proof required")
        record_id = new_uuid7()
        context = FieldContext(
            tenant, original_owner_person_id, record_id,
            self._field_type, self._authority,
        )
        nonce = secrets.token_bytes(12)
        await self._nonce_registry.reserve(
            tenant_id=tenant, aes_key_identity=key_ref.key_identity, nonce_96bit=nonce
        )
        encrypted = seal_phone_aesgcm(
            phone_e164=normalized,
            context=context,
            key=key_ref.key,
            nonce_96bit=nonce,
        )
        # Explicitly non-unique phone blind index: shared family numbers allowed.
        await self._scope.session.execute(
            text(
                """
                INSERT INTO person_phones (
                  id, tenant_id, person_id, phone_ciphertext, nonce_96bit,
                  auth_tag_128bit, encryption_key_version, aad_version,
                  masked_phone, phone_lookup_hmac, hmac_key_version,
                  is_primary, is_shared_phone, phone_verified_at_utc,
                  created_at_utc
                ) VALUES (
                  :record_id, :tenant, :owner, :ciphertext, :nonce,
                  :tag, :key_version, :aad_version, :masked,
                  :digest, :digest_version, :is_primary, :is_shared,
                  NULL, :created_at
                )
                """
            ),
            {
                "record_id": record_id,
                "tenant": tenant,
                "owner": original_owner_person_id,
                "ciphertext": encrypted.phone_ciphertext,
                "nonce": encrypted.nonce_96bit,
                "tag": encrypted.auth_tag_128bit,
                "key_version": encrypted.encryption_key_version,
                "aad_version": encrypted.aad_version,
                "masked": mask_phone_e164(normalized),
                "digest": lookup.digest,
                "digest_version": lookup.key_version,
                "is_primary": bool(is_primary),
                "is_shared": bool(is_shared_phone),
                "created_at": datetime.now(timezone.utc),
            },
        )
        await SqlAuditStore(self._scope.session).append(
            tenant_id=tenant,
            actor_type="USER",
            actor_id=principal,
            operation="person_phone.created",
            target_type="person_phone",
            target_id=record_id,
            details={
                "aad_version": 1,
                "encryption_key_version": key_ref.key.version,
                "hmac_key_version": lookup.key_version,
            },
        )
        return record_id
