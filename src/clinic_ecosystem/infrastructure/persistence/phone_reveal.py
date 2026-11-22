"""Separate least-privilege phone plaintext read boundary for M1-02.

Never call from generic search/list endpoints. The caller must have an explicit
approved reveal permission and must use a verified JWT tenant SQL transaction.
Actual KMS key retrieval and phone AAD token ratification remain external.

Plaintext is returned ONLY after the access-audit row is committed (durable).
"""
from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import text

from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.authenticated_uow import (
    VerifiedTenantDbSession,
)
from clinic_ecosystem.infrastructure.persistence.permissions import SqlPermissionService
from clinic_ecosystem.infrastructure.persistence.phone_vault import TenantPhoneEncryptionKey
from clinic_ecosystem.shared_kernel.pii_encryption import (
    EncryptedPhone, FieldContext, decrypt_phone,
)


class PhoneRevealRejected(PermissionError):
    pass


class PhoneDecryptionKeyProvider(Protocol):
    async def phone_aes_key_for_version(
        self, *, tenant_id: UUID, encryption_key_version: int
    ) -> TenantPhoneEncryptionKey:
        """Return the exact historical authorized tenant key, not simply latest."""


class SqlPhoneReader:
    def __init__(
        self,
        *,
        scope: VerifiedTenantDbSession,
        key_provider: PhoneDecryptionKeyProvider,
        phone_field_type: str,
        phone_issuing_authority: str,
        reveal_permission_code: str,
    ) -> None:
        # Reject forged scopes: construction without mint token fails in __post_init__.
        if type(scope) is not VerifiedTenantDbSession:
            raise TypeError("verified tenant SQL transaction is required")
        # Touch auth marker (raises if forged without token via dataclass replace tricks).
        if getattr(scope, "_auth", None) is None:
            raise TypeError("verified tenant SQL transaction is required")
        if not callable(getattr(key_provider, "phone_aes_key_for_version", None)):
            raise TypeError("historical authorized tenant KMS key provider is required")
        if not phone_field_type or not phone_issuing_authority:
            raise ValueError("exact signed phone AAD tokens are required")
        if not reveal_permission_code or not reveal_permission_code.isascii():
            raise ValueError("distinct, configured phone reveal RBAC permission required")
        self._scope = scope
        self._keys = key_provider
        self._field_type = phone_field_type
        self._authority = phone_issuing_authority
        self._permission = reveal_permission_code

    async def reveal(self, *, phone_record_id: UUID) -> str:
        if not isinstance(phone_record_id, UUID):
            raise TypeError("phone record id must be a UUID")
        await self._scope.assert_tenant_guc()
        tenant = self._scope.principal.tenant_id
        principal = self._scope.principal.principal_id

        allowed = await SqlPermissionService(self._scope.session).principal_has(
            tenant_id=tenant, principal_id=principal,
            permission_code=self._permission,
        )
        if not allowed:
            raise PhoneRevealRejected("phone plaintext reveal denied")

        result = await self._scope.session.execute(
            text(
                """
                SELECT id, person_id, phone_ciphertext, nonce_96bit,
                       auth_tag_128bit, encryption_key_version, aad_version
                FROM person_phones
                WHERE tenant_id = :tenant AND id = :phone_id
                """
            ),
            {"tenant": tenant, "phone_id": phone_record_id},
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise PhoneRevealRejected("phone not found in authenticated tenant")

        version = row["encryption_key_version"]
        sealed = EncryptedPhone(
            phone_ciphertext=bytes(row["phone_ciphertext"]),
            nonce_96bit=bytes(row["nonce_96bit"]),
            auth_tag_128bit=bytes(row["auth_tag_128bit"]),
            encryption_key_version=version,
            aad_version=row["aad_version"],
        )
        person_id = row["person_id"]
        record_id = row["id"]

        ref = await self._keys.phone_aes_key_for_version(
            tenant_id=tenant, encryption_key_version=version
        )
        if (
            not isinstance(ref, TenantPhoneEncryptionKey)
            or ref.tenant_id != tenant
            or ref.key.version != version
        ):
            raise PhoneRevealRejected("historical KMS key boundary mismatch")

        context = FieldContext(
            tenant, person_id, record_id,
            self._field_type, self._authority,
        )
        # Cryptographic validity BEFORE audit+commit so InvalidTag does not
        # leave a successful reveal audit for a non-decryptable payload.
        # Plaintext is held only in process memory and returned AFTER durable audit.
        plaintext = decrypt_phone(encrypted=sealed, context=context, key=ref.key)

        await SqlAuditStore(self._scope.session).append(
            tenant_id=tenant,
            actor_type="USER",
            actor_id=principal,
            operation="person_phone.plaintext_revealed",
            target_type="person_phone",
            target_id=phone_record_id,
            details={"aad_version": sealed.aad_version, "key_version": version},
        )
        # Commit audit before plaintext crosses the API boundary.
        await self._scope.commit_security_checkpoint()
        return plaintext
