"""Encrypted phone persistence on TP0002 person_phones (shared-family, non-unique)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.infrastructure.crypto.pii_box import (
    KEY_VERSION,
    PiiKeys,
    normalize_phone_e164,
    phone_lookup_digest,
    seal_phone,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


@dataclass(frozen=True, slots=True)
class PhoneSearchHit:
    phone_id: UUID
    person_id: UUID
    patient_profile_id: UUID | None
    first_name: str
    last_name: str
    masked_phone: str
    is_shared_phone: bool
    is_primary: bool
    is_active: bool | None


class SqlPersonPhoneStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        tenant_id: UUID,
        person_id: UUID,
        phone: str,
        keys: PiiKeys,
        is_primary: bool = True,
        is_shared_phone: bool = False,
        now: datetime | None = None,
    ) -> UUID:
        e164 = normalize_phone_e164(phone)
        record_id = new_uuid7()
        sealed = seal_phone(
            tenant_id=tenant_id,
            person_id=person_id,
            record_id=record_id,
            e164=e164,
            keys=keys,
        )
        current = now or datetime.now(timezone.utc)
        await self._session.execute(
            text(
                """
                INSERT INTO person_phones (
                    id, tenant_id, person_id, phone_ciphertext, nonce_96bit,
                    auth_tag_128bit, encryption_key_version, aad_version,
                    masked_phone, phone_lookup_hmac, hmac_key_version,
                    is_primary, is_shared_phone, phone_verified_at_utc, created_at_utc
                ) VALUES (
                    :id, :tenant_id, :person_id, :ciphertext, :nonce,
                    :tag, :enc_ver, :aad_ver,
                    :masked, :hmac, :hmac_ver,
                    :is_primary, :is_shared, NULL, :now
                )
                """
            ),
            {
                "id": record_id,
                "tenant_id": tenant_id,
                "person_id": person_id,
                "ciphertext": sealed.ciphertext,
                "nonce": sealed.nonce_96bit,
                "tag": sealed.auth_tag_128bit,
                "enc_ver": sealed.encryption_key_version,
                "aad_ver": sealed.aad_version,
                "masked": sealed.masked_display,
                "hmac": sealed.lookup_hmac,
                "hmac_ver": sealed.hmac_key_version,
                "is_primary": is_primary,
                "is_shared": is_shared_phone,
                "now": current,
            },
        )
        return record_id

    async def search_by_phone(
        self,
        *,
        tenant_id: UUID,
        phone: str,
        keys: PiiKeys,
        hmac_key_version: int = KEY_VERSION,
        limit: int = 20,
    ) -> list[PhoneSearchHit]:
        e164 = normalize_phone_e164(phone)
        digest = phone_lookup_digest(tenant_id=tenant_id, e164=e164, keys=keys)
        result = await self._session.execute(
            text(
                """
                SELECT DISTINCT ON (pp.person_id)
                       ph.id AS phone_id, ph.person_id, ph.masked_phone,
                       ph.is_shared_phone, ph.is_primary,
                       pp.id AS patient_profile_id, pp.is_active,
                       tp.first_name, tp.last_name
                FROM person_phones ph
                JOIN tenant_persons tp
                  ON tp.tenant_id = ph.tenant_id AND tp.id = ph.person_id
                LEFT JOIN patient_profiles pp
                  ON pp.tenant_id = ph.tenant_id AND pp.person_id = ph.person_id
                WHERE ph.tenant_id = :tenant_id
                  AND ph.hmac_key_version = :hmac_ver
                  AND ph.phone_lookup_hmac = :digest
                ORDER BY ph.person_id, ph.is_primary DESC, ph.created_at_utc ASC
                LIMIT :limit
                """
            ),
            {
                "tenant_id": tenant_id,
                "hmac_ver": hmac_key_version,
                "digest": digest,
                "limit": limit,
            },
        )
        return [
            PhoneSearchHit(
                phone_id=row["phone_id"],
                person_id=row["person_id"],
                patient_profile_id=row["patient_profile_id"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                masked_phone=row["masked_phone"],
                is_shared_phone=bool(row["is_shared_phone"]),
                is_primary=bool(row["is_primary"]),
                is_active=None if row["is_active"] is None else bool(row["is_active"]),
            )
            for row in result.mappings().all()
        ]
