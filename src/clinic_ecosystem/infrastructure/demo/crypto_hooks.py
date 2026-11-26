"""Optional PII crypto hooks — seal phones/National IDs when CLINIC_PII_* keys exist."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_ecosystem.infrastructure.crypto.pii_box import (
    CryptoUnavailable,
    PiiKeys,
    SealedBox,
    load_pii_keys,
    seal_identifier,
    seal_phone,
)
from clinic_ecosystem.infrastructure.demo.builders_people import PatientRow
from clinic_ecosystem.infrastructure.demo.ids import demo_uuid
from clinic_ecosystem.infrastructure.demo.profiles import DemoTargets


@dataclass(frozen=True)
class IdentifierInsert:
    id: UUID
    person_id: UUID
    sealed: SealedBox
    id_type: str = "IR_NATIONAL_ID"
    authority: str = "IR-CIVIL-REGISTRY"


@dataclass(frozen=True)
class PhoneInsert:
    id: UUID
    person_id: UUID
    sealed: SealedBox
    is_primary: bool
    is_shared_phone: bool


@dataclass
class CryptoSeedPlan:
    available: bool
    keys: PiiKeys | None
    identifiers: list[IdentifierInsert]
    phones: list[PhoneInsert]
    skip_reason: str | None = None


def try_load_keys() -> tuple[PiiKeys | None, str | None]:
    try:
        return load_pii_keys(), None
    except CryptoUnavailable as exc:
        return None, str(exc)


def plan_crypto_rows(
    targets: DemoTargets,
    *,
    tenant_id: UUID,
    patients: list[PatientRow],
) -> CryptoSeedPlan:
    keys, reason = try_load_keys()
    if keys is None:
        return CryptoSeedPlan(
            available=False,
            keys=None,
            identifiers=[],
            phones=[],
            skip_reason=reason or "CLINIC_PII_* keys unavailable",
        )

    identifiers: list[IdentifierInsert] = []
    phones: list[PhoneInsert] = []
    for i, patient in enumerate(patients):
        if patient.national_id:
            record_id = demo_uuid(targets.seed, "person_identifier", i)
            # Deterministic nonce from seed for reproducible ciphertext in demos.
            nonce = demo_uuid(targets.seed, "nid_nonce", i).bytes[:12]
            sealed = seal_identifier(
                keys=keys,
                tenant_id=tenant_id,
                person_id=patient.person_id,
                record_id=record_id,
                id_type="IR_NATIONAL_ID",
                issuing_country_or_authority="IR-CIVIL-REGISTRY",
                normalized_value=patient.national_id,
                nonce=nonce,
            )
            identifiers.append(
                IdentifierInsert(id=record_id, person_id=patient.person_id, sealed=sealed)
            )
        if patient.phone_e164:
            record_id = demo_uuid(targets.seed, "person_phone", i)
            nonce = demo_uuid(targets.seed, "phone_nonce", i).bytes[:12]
            sealed = seal_phone(
                keys=keys,
                tenant_id=tenant_id,
                person_id=patient.person_id,
                record_id=record_id,
                e164=patient.phone_e164,
                nonce=nonce,
            )
            phones.append(
                PhoneInsert(
                    id=record_id,
                    person_id=patient.person_id,
                    sealed=sealed,
                    is_primary=True,
                    is_shared_phone=patient.shared_phone_family is not None,
                )
            )
    return CryptoSeedPlan(
        available=True,
        keys=keys,
        identifiers=identifiers,
        phones=phones,
        skip_reason=None,
    )


def preview_demo_pii_env(seed: int = 20261126) -> dict[str, str]:
    """Deterministic non-prod key material for preview stacks (not for production)."""
    import hashlib

    aes = hashlib.sha256(f"clinic-demo-aes:{seed}".encode()).hexdigest()
    hmac_key = hashlib.sha256(f"clinic-demo-hmac:{seed}".encode()).hexdigest()
    return {
        "CLINIC_PII_AES_KEY": aes,
        "CLINIC_PII_HMAC_KEY": hmac_key,
        "CLINIC_PII_AES_KEY_VERSION": "1",
        "CLINIC_PII_HMAC_KEY_VERSION": "1",
    }


# Silence unused import for type checkers using datetime in callers.
_ = datetime
