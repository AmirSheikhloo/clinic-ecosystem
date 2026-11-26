"""AES-256-GCM + domain-separated HMAC blind indexes (spec §52 / 766–770).

NON-PRODUCTION: keys from CLINIC_PII_AES_KEY_HEX / CLINIC_PII_HMAC_KEY_HEX
(or CLINIC_PII_AES_KEY / CLINIC_PII_HMAC_KEY). Refuse outside non-prod CLINIC_ENV.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass, field
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from clinic_ecosystem.domain.identity.national_id import normalize_ascii_digits

KEY_VERSION = 1
AAD_VERSION = 1
NONCE_LEN = 12
TAG_LEN = 16
_NON_PROD = frozenset({"test", "development", "dev", "local", "preview"})
_E164 = re.compile(r"\+[1-9][0-9]{1,14}\Z", flags=re.ASCII)
PHONE_FIELD = "PHONE_E164"
PHONE_AUTH = "E164"


class CryptoUnavailable(RuntimeError):
    code = "identifier_crypto_unavailable"


@dataclass(frozen=True, slots=True)
class PiiKeys:
    aes_key: bytes = field(repr=False)
    hmac_key: bytes = field(repr=False)
    key_version: int = KEY_VERSION


@dataclass(frozen=True, slots=True)
class SealedBox:
    ciphertext: bytes = field(repr=False)
    nonce_96bit: bytes = field(repr=False)
    auth_tag_128bit: bytes = field(repr=False)
    lookup_hmac: bytes = field(repr=False)
    masked_display: str
    encryption_key_version: int = KEY_VERSION
    aad_version: int = AAD_VERSION
    hmac_key_version: int = KEY_VERSION


def _hex_key(raw: str | None, *, name: str, exact: int | None = None, minimum: int | None = None) -> bytes:
    if not raw or not raw.strip():
        raise CryptoUnavailable(f"{name} is not set")
    value = raw.strip()
    try:
        if value.startswith("hex:"):
            material = bytes.fromhex(value[4:])
        else:
            material = bytes.fromhex(value)
    except ValueError as exc:
        raise CryptoUnavailable(f"{name} is not valid hex") from exc
    if exact is not None and len(material) != exact:
        raise CryptoUnavailable(f"{name} must be exactly {exact} bytes")
    if minimum is not None and len(material) < minimum:
        raise CryptoUnavailable(f"{name} must be at least {minimum} bytes")
    return material


def load_pii_keys(environ: dict[str, str] | None = None) -> PiiKeys:
    env = environ if environ is not None else os.environ
    clinic_env = (env.get("CLINIC_ENV") or "production").strip().lower()
    if clinic_env not in _NON_PROD:
        raise CryptoUnavailable("PII env keys are not permitted outside non-production")
    aes = _hex_key(
        env.get("CLINIC_PII_AES_KEY_HEX") or env.get("CLINIC_PII_AES_KEY"),
        name="CLINIC_PII_AES_KEY_HEX",
        exact=32,
    )
    hmac_key = _hex_key(
        env.get("CLINIC_PII_HMAC_KEY_HEX") or env.get("CLINIC_PII_HMAC_KEY"),
        name="CLINIC_PII_HMAC_KEY_HEX",
        minimum=32,
    )
    return PiiKeys(aes_key=aes, hmac_key=hmac_key, key_version=KEY_VERSION)


def aad_v1(
    *,
    tenant_id: UUID,
    person_id: UUID,
    record_id: UUID,
    id_type_or_field_type: str,
    issuing_country_or_authority: str,
) -> bytes:
    return (
        "v1|"
        + str(tenant_id).lower()
        + "|"
        + str(person_id).lower()
        + "|"
        + str(record_id).lower()
        + "|"
        + id_type_or_field_type.strip().upper()
        + "|"
        + issuing_country_or_authority.strip().upper()
    ).encode("utf-8")


def identifier_hmac_message(
    *,
    tenant_id: UUID,
    id_type: str,
    issuing_country_or_authority: str,
    normalized_value: str,
) -> bytes:
    return (
        str(tenant_id).lower()
        + "|"
        + id_type.strip().upper()
        + "|"
        + issuing_country_or_authority.strip().upper()
        + "|"
        + normalized_value
    ).encode("utf-8")


def phone_hmac_message(*, tenant_id: UUID, e164: str) -> bytes:
    return f"{str(tenant_id).lower()}|{PHONE_FIELD}|{PHONE_AUTH}|{e164}".encode("utf-8")


def mask_national_id(value: str) -> str:
    digits = "".join(ch for ch in normalize_ascii_digits(value) if ch.isdigit())
    if len(digits) < 4:
        return "****"
    return ("*" * max(0, len(digits) - 4)) + digits[-4:]


def mask_phone(e164: str) -> str:
    digits = "".join(ch for ch in e164 if ch.isdigit())
    if len(digits) < 4:
        return "****"
    return "****" + digits[-4:]


def normalize_phone_e164(value: str, *, default_region: str = "IR") -> str:
    raw = normalize_ascii_digits(value)
    cleaned = re.sub(r"[\s\-().]", "", raw)
    if not cleaned:
        raise ValueError("phone_empty")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if cleaned.startswith("+"):
        candidate = cleaned
    elif default_region == "IR":
        digits = "".join(ch for ch in cleaned if ch.isdigit())
        if digits.startswith("98") and len(digits) >= 12:
            candidate = "+" + digits
        elif digits.startswith("0") and len(digits) == 11:
            candidate = "+98" + digits[1:]
        elif digits.startswith("9") and len(digits) == 10:
            candidate = "+98" + digits
        else:
            raise ValueError("phone_invalid")
    else:
        raise ValueError("phone_invalid")
    if not _E164.fullmatch(candidate):
        raise ValueError("phone_invalid")
    return candidate


def identifier_lookup_digest(
    *,
    tenant_id: UUID,
    id_type: str,
    issuing_country_or_authority: str,
    normalized_value: str,
    keys: PiiKeys,
) -> bytes:
    return hmac.new(
        keys.hmac_key,
        identifier_hmac_message(
            tenant_id=tenant_id,
            id_type=id_type,
            issuing_country_or_authority=issuing_country_or_authority,
            normalized_value=normalized_value,
        ),
        hashlib.sha256,
    ).digest()


def phone_lookup_digest(*, tenant_id: UUID, e164: str, keys: PiiKeys) -> bytes:
    return hmac.new(
        keys.hmac_key,
        phone_hmac_message(tenant_id=tenant_id, e164=e164),
        hashlib.sha256,
    ).digest()


def seal_identifier(
    *,
    tenant_id: UUID,
    person_id: UUID,
    record_id: UUID,
    id_type: str,
    issuing_country_or_authority: str,
    normalized_value: str,
    keys: PiiKeys,
    nonce: bytes | None = None,
) -> SealedBox:
    aad = aad_v1(
        tenant_id=tenant_id,
        person_id=person_id,
        record_id=record_id,
        id_type_or_field_type=id_type,
        issuing_country_or_authority=issuing_country_or_authority,
    )
    nonce = nonce if nonce is not None else secrets.token_bytes(NONCE_LEN)
    if len(nonce) != NONCE_LEN:
        raise ValueError("nonce must be 12 bytes")
    sealed = AESGCM(keys.aes_key).encrypt(nonce, normalized_value.encode("utf-8"), aad)
    return SealedBox(
        ciphertext=sealed[:-TAG_LEN],
        nonce_96bit=nonce,
        auth_tag_128bit=sealed[-TAG_LEN:],
        lookup_hmac=identifier_lookup_digest(
            tenant_id=tenant_id,
            id_type=id_type,
            issuing_country_or_authority=issuing_country_or_authority,
            normalized_value=normalized_value,
            keys=keys,
        ),
        masked_display=(
            mask_national_id(normalized_value)
            if id_type.upper() == "IR_NATIONAL_ID"
            else ("****" + normalized_value[-4:] if len(normalized_value) >= 4 else "****")
        ),
        encryption_key_version=keys.key_version,
        hmac_key_version=keys.key_version,
    )


def open_identifier(
    *,
    tenant_id: UUID,
    person_id: UUID,
    record_id: UUID,
    id_type: str,
    issuing_country_or_authority: str,
    ciphertext: bytes,
    nonce_96bit: bytes,
    auth_tag_128bit: bytes,
    keys: PiiKeys,
) -> str:
    aad = aad_v1(
        tenant_id=tenant_id,
        person_id=person_id,
        record_id=record_id,
        id_type_or_field_type=id_type,
        issuing_country_or_authority=issuing_country_or_authority,
    )
    return AESGCM(keys.aes_key).decrypt(
        nonce_96bit, ciphertext + auth_tag_128bit, aad
    ).decode("utf-8")


def seal_phone(
    *,
    tenant_id: UUID,
    person_id: UUID,
    record_id: UUID,
    e164: str,
    keys: PiiKeys,
    nonce: bytes | None = None,
) -> SealedBox:
    aad = aad_v1(
        tenant_id=tenant_id,
        person_id=person_id,
        record_id=record_id,
        id_type_or_field_type=PHONE_FIELD,
        issuing_country_or_authority=PHONE_AUTH,
    )
    nonce = nonce if nonce is not None else secrets.token_bytes(NONCE_LEN)
    if len(nonce) != NONCE_LEN:
        raise ValueError("nonce must be 12 bytes")
    sealed = AESGCM(keys.aes_key).encrypt(nonce, e164.encode("ascii"), aad)
    return SealedBox(
        ciphertext=sealed[:-TAG_LEN],
        nonce_96bit=nonce,
        auth_tag_128bit=sealed[-TAG_LEN:],
        lookup_hmac=phone_lookup_digest(tenant_id=tenant_id, e164=e164, keys=keys),
        masked_display=mask_phone(e164),
        encryption_key_version=keys.key_version,
        hmac_key_version=keys.key_version,
    )


def open_phone(
    *,
    tenant_id: UUID,
    person_id: UUID,
    record_id: UUID,
    ciphertext: bytes,
    nonce_96bit: bytes,
    auth_tag_128bit: bytes,
    keys: PiiKeys,
) -> str:
    aad = aad_v1(
        tenant_id=tenant_id,
        person_id=person_id,
        record_id=record_id,
        id_type_or_field_type=PHONE_FIELD,
        issuing_country_or_authority=PHONE_AUTH,
    )
    return AESGCM(keys.aes_key).decrypt(
        nonce_96bit, ciphertext + auth_tag_128bit, aad
    ).decode("ascii")
