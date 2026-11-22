"""Pure PII input contracts for Package-1 identity/HMAC design.

Source: frozen v3.0.1 clauses 765, 767, 768, 769, 770, 771 and 772.
No KMS access, ciphertext persistence, nonce allocation, or database writes here.
Phone AAD field/authority tokens must be passed explicitly until signed.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from dataclasses import dataclass, field

_E164 = re.compile(r"\+[1-9][0-9]{1,14}\Z", flags=re.ASCII)
_ASCII_TOKEN = re.compile(r"[A-Z0-9][A-Z0-9_.-]*\Z", flags=re.ASCII)


def _uuid_string(value: uuid.UUID) -> str:
    if not isinstance(value, uuid.UUID):
        raise TypeError("expected an authenticated uuid.UUID, not caller-provided text")
    return str(value)


def _token(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    canonical = value.strip().upper()
    if not _ASCII_TOKEN.fullmatch(canonical):
        raise ValueError(f"{name} must be a nonempty unambiguous ASCII token")
    return canonical


def _aad_token(value: str, name: str) -> str:
    """AAD has UPPER but no TRIM in frozen Clause 770: reject whitespace."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if value != value.strip():
        raise ValueError(f"{name} cannot contain surrounding whitespace")
    canonical = value.upper()
    if not _ASCII_TOKEN.fullmatch(canonical):
        raise ValueError(f"{name} must be an unambiguous ASCII contract token")
    return canonical


def canonical_aad_tokens(field_type: str, authority: str) -> tuple[str, str]:
    """Validate configured AAD tokens; does not sign or approve their meaning."""
    return _aad_token(field_type, "field_type"), _aad_token(authority, "authority")


def mask_phone_e164(value: str) -> str:
    """Never reveal a whole short phone number or the international + prefix."""
    digits = require_e164(value)[1:]
    return "****" if len(digits) < 7 else "****" + digits[-4:]


def require_e164(value: str) -> str:
    """Accept only an *already normalized* E.164 string, without inferring country.

    This is format validation, not evidence that the phone was verified.
    """
    if not isinstance(value, str):
        raise TypeError("phone must be text")
    if not _E164.fullmatch(value):
        raise ValueError("phone must be strictly normalized E.164")
    return value


@dataclass(frozen=True)
class HmacKey:
    """A caller-supplied versioned secret; never log or persist key material."""
    version: int
    material: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.version) is not int or not 1 <= self.version <= 32767:
            raise ValueError("HMAC version must fit a positive PostgreSQL SMALLINT")
        if type(self.material) is not bytes or len(self.material) < 32:
            raise ValueError("HMAC secret must be at least 32 bytes")


@dataclass(frozen=True)
class LookupDigest:
    key_version: int
    digest: bytes

    def __post_init__(self) -> None:
        if type(self.key_version) is not int or not 1 <= self.key_version <= 32767:
            raise ValueError("lookup key version must be a positive SMALLINT")
        if not isinstance(self.digest, bytes) or len(self.digest) != 32:
            raise ValueError("blind-index digest must be exactly 32 bytes")


_PERSIAN_ARABIC_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"
)


def map_identifier_digits(value: str) -> str:
    """Clause 765 digit mapping only; NOT full type-specific normalization.

    Callers must still apply approved separator, length, character-set and
    check-digit rules before passing the value to identifier_input().
    """
    if not isinstance(value, str):
        raise TypeError("identifier must be text")
    return value.translate(_PERSIAN_ARABIC_DIGITS)


def normalized_iran_national_id(value: str) -> str:
    """Clause 765: syntactic Iranian National ID validation ONLY, not ownership.

    Digit conversion is permitted; unspecified separator/whitespace policy is
    intentionally not guessed. Invalid/check-digit-only identities fail closed.
    """
    canonical = map_identifier_digits(value)
    if len(canonical) != 10 or not canonical.isascii() or not canonical.isdecimal():
        raise ValueError("Iranian national ID must have exactly 10 ASCII digits")
    if len(set(canonical)) == 1:
        raise ValueError("repeated-digit national ID is syntactically invalid")
    remainder = sum(int(ch) * (10 - i) for i, ch in enumerate(canonical[:9])) % 11
    expected_check = remainder if remainder < 2 else 11 - remainder
    if int(canonical[9]) != expected_check:
        raise ValueError("Iranian national ID check digit mismatch")
    return canonical


def identifier_input(
    *,
    tenant_id: uuid.UUID,
    id_type: str,
    issuing_country_or_authority: str,
    normalized_identifier_value: str,
) -> bytes:
    """Exact Clause 767 domain-separated format; callers perform type-specific
    validation/normalization first, including Persian/Arabic digit conversion.
    The leading zeros of the *provided* identifier are never discarded.
    """
    kind = _token(id_type, "id_type")
    authority = _token(issuing_country_or_authority, "issuing_country_or_authority")
    if kind not in {"IR_NATIONAL_ID", "FOREIGN_FIDA_CODE", "FOREIGN_PASSPORT"}:
        raise ValueError("identifier type must match frozen TP0002 enum")
    value = normalized_identifier_value
    if not isinstance(value, str):
        raise TypeError("identifier must be normalized text")
    if not value or value != value.strip() or "|" in value or any(
        ord(ch) < 32 or ord(ch) == 127
        or (ch.isdecimal() and not ("0" <= ch <= "9"))
        for ch in value
    ):
        raise ValueError("identifier must be nonempty pre-normalized text")
    # Deliberately do not guess the identifier-type-specific canonicalization.
    return f"{_uuid_string(tenant_id)}|{kind}|{authority}|{value}".encode("utf-8")


def identifier_lookup_hmac(*, key: HmacKey, canonical_input: bytes) -> LookupDigest:
    if not isinstance(key, HmacKey):
        raise TypeError("key must be a HmacKey from the trusted key provider")
    if type(canonical_input) is not bytes or not canonical_input:
        raise ValueError("canonical input must be nonempty bytes")
    return LookupDigest(
        key_version=key.version,
        digest=hmac.new(key.material, canonical_input, hashlib.sha256).digest(),
    )


def dual_identifier_lookup_hmac(
    *, active_key: HmacKey, next_key: HmacKey, canonical_input: bytes
) -> tuple[LookupDigest, LookupDigest]:
    """Compute both versions from the same immutable canonical input.

    Callers MUST persist both in one database write transaction; this helper
    does not assert that a writer drain, SQL constraint, or cutover happened.
    """
    if active_key.version == next_key.version:
        raise ValueError("active and next HMAC versions must differ")
    if hmac.compare_digest(active_key.material, next_key.material):
        raise ValueError("key rotation cannot reuse the same secret")
    return (
        identifier_lookup_hmac(key=active_key, canonical_input=canonical_input),
        identifier_lookup_hmac(key=next_key, canonical_input=canonical_input),
    )


def aad_v1(
    *,
    tenant_id: uuid.UUID,
    original_person_id: uuid.UUID,
    record_id: uuid.UUID,
    id_type_or_field_type: str,
    issuing_country_or_authority: str,
) -> bytes:
    """Exact frozen Clause 770 AAD-v1 structure.

    Use the immutable ORIGINAL person owner through an alias merge. The tokens
    are explicit input, never undocumented PHONE_E164/E164 production defaults.
    The result binds tenant/person/record/type/authority, not key-version.
    """
    return (
        "v1|"
        + _uuid_string(tenant_id)
        + "|"
        + _uuid_string(original_person_id)
        + "|"
        + _uuid_string(record_id)
        + "|"
        + _aad_token(id_type_or_field_type, "id_type_or_field_type")
        + "|"
        + _aad_token(issuing_country_or_authority, "issuing_country_or_authority")
    ).encode("utf-8")
