"""Encrypted official-identifier persistence on TP0002 person_identifiers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.infrastructure.crypto.pii_box import (
    PiiKeys,
    identifier_lookup_digest,
    seal_identifier,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

ID_TYPES = frozenset({"IR_NATIONAL_ID", "FOREIGN_FIDA_CODE", "FOREIGN_PASSPORT"})


class DuplicateOfficialIdentifier(Exception):
    """Active blind-index uniqueness collision within tenant/type/authority."""


@dataclass(frozen=True, slots=True)
class IdentifierLookupHit:
    identifier_id: UUID
    person_id: UUID
    patient_profile_id: UUID | None
    id_type: str
    issuing_country_or_authority: str
    masked_display: str
    verification_status: str
    first_name: str | None
    last_name: str | None


class SqlPersonIdentifierStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        tenant_id: UUID,
        person_id: UUID,
        id_type: str,
        issuing_country_or_authority: str,
        normalized_value: str,
        keys: PiiKeys,
        verification_status: str = "SYNTACTICALLY_VALID_UNVERIFIED",
        now: datetime | None = None,
    ) -> UUID:
        kind = id_type.strip().upper()
        if kind not in ID_TYPES:
            raise ValueError("id_type_invalid")
        authority = issuing_country_or_authority.strip().upper()
        record_id = new_uuid7()
        sealed = seal_identifier(
            tenant_id=tenant_id,
            person_id=person_id,
            record_id=record_id,
            id_type=kind,
            issuing_country_or_authority=authority,
            normalized_value=normalized_value,
            keys=keys,
        )
        current = now or datetime.now(timezone.utc)
        try:
            await self._session.execute(
                text(
                    """
                    INSERT INTO person_identifiers (
                        id, tenant_id, person_id, id_type, issuing_country_or_authority,
                        id_ciphertext, nonce_96bit, auth_tag_128bit,
                        encryption_key_version, aad_version, masked_display,
                        verification_status, lookup_hmac_active, hmac_key_version_active,
                        lookup_hmac_next, hmac_key_version_next, created_at_utc
                    ) VALUES (
                        :id, :tenant_id, :person_id, :id_type, :authority,
                        :ciphertext, :nonce, :tag,
                        :enc_ver, :aad_ver, :masked,
                        :verification, :hmac, :hmac_ver,
                        NULL, NULL, :now
                    )
                    """
                ),
                {
                    "id": record_id,
                    "tenant_id": tenant_id,
                    "person_id": person_id,
                    "id_type": kind,
                    "authority": authority,
                    "ciphertext": sealed.ciphertext,
                    "nonce": sealed.nonce_96bit,
                    "tag": sealed.auth_tag_128bit,
                    "enc_ver": sealed.encryption_key_version,
                    "aad_ver": sealed.aad_version,
                    "masked": sealed.masked_display,
                    "verification": verification_status,
                    "hmac": sealed.lookup_hmac,
                    "hmac_ver": sealed.hmac_key_version,
                    "now": current,
                },
            )
        except IntegrityError as exc:
            raise DuplicateOfficialIdentifier("duplicate_official_identifier") from exc
        return record_id

    async def lookup_exact(
        self,
        *,
        tenant_id: UUID,
        id_type: str,
        issuing_country_or_authority: str,
        normalized_value: str,
        keys: PiiKeys,
    ) -> IdentifierLookupHit | None:
        kind = id_type.strip().upper()
        authority = issuing_country_or_authority.strip().upper()
        digest = identifier_lookup_digest(
            tenant_id=tenant_id,
            id_type=kind,
            issuing_country_or_authority=authority,
            normalized_value=normalized_value,
            keys=keys,
        )
        result = await self._session.execute(
            text(
                """
                SELECT pi.id AS identifier_id, pi.person_id, pi.id_type,
                       pi.issuing_country_or_authority, pi.masked_display,
                       pi.verification_status, pp.id AS patient_profile_id,
                       tp.first_name, tp.last_name
                FROM person_identifiers pi
                JOIN tenant_persons tp
                  ON tp.tenant_id = pi.tenant_id AND tp.id = pi.person_id
                LEFT JOIN patient_profiles pp
                  ON pp.tenant_id = pi.tenant_id AND pp.person_id = pi.person_id
                WHERE pi.tenant_id = :tenant_id
                  AND pi.id_type = :id_type
                  AND pi.issuing_country_or_authority = :authority
                  AND pi.lookup_hmac_active = :digest
                LIMIT 1
                """
            ),
            {
                "tenant_id": tenant_id,
                "id_type": kind,
                "authority": authority,
                "digest": digest,
            },
        )
        row = result.mappings().first()
        if row is None:
            return None
        return IdentifierLookupHit(
            identifier_id=row["identifier_id"],
            person_id=row["person_id"],
            patient_profile_id=row["patient_profile_id"],
            id_type=row["id_type"],
            issuing_country_or_authority=row["issuing_country_or_authority"],
            masked_display=row["masked_display"],
            verification_status=row["verification_status"],
            first_name=row["first_name"],
            last_name=row["last_name"],
        )

    async def exists_duplicate(
        self,
        *,
        tenant_id: UUID,
        id_type: str,
        issuing_country_or_authority: str,
        normalized_value: str,
        keys: PiiKeys,
    ) -> bool:
        hit = await self.lookup_exact(
            tenant_id=tenant_id,
            id_type=id_type,
            issuing_country_or_authority=issuing_country_or_authority,
            normalized_value=normalized_value,
            keys=keys,
        )
        return hit is not None
