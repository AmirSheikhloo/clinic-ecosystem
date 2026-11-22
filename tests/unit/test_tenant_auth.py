"""Synthetic RSA/EC JWT trust-boundary tests. Not a live IdP/revocation proof."""
from __future__ import annotations

import time
from uuid import UUID
from dataclasses import replace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from clinic_ecosystem.shared_kernel.tenant_auth import (
    AuthenticationRejected,
    HumanJwtVerifier,
    TrustedJwtPublicKey,
)

TENANT = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PRINCIPAL = UUID("11111111-1111-1111-1111-111111111111")


class SyntheticJtiGuard:
    def __init__(self, reject=False):
        self.reject = reject
        self.calls = []

    async def ensure_active(self, *, tenant_id: UUID, token_jti: str) -> None:
        self.calls.append((tenant_id, token_jti))
        if self.reject:
            raise AuthenticationRejected("token revoked or store unavailable")


@pytest.fixture(scope="module")
def keypairs():
    rsa_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ec_private = ec.generate_private_key(ec.SECP256R1())
    result = []
    for kid, alg, private in (("rsa-a", "RS256", rsa_private), ("ec-b", "ES256", ec_private)):
        public_pem = private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        result.append((kid, alg, private, TrustedJwtPublicKey(kid, alg, public_pem)))
    return result


def claims(**changes):
    now = int(time.time())
    base = {
        "iss": "https://idp.example.invalid/tenant",
        "aud": "clinic-api",
        "sub": str(PRINCIPAL),
        "tenant_id": str(TENANT),
        "jti": "synthetic-jti-001",
        "iat": now - 2,
        "nbf": now - 2,
        "exp": now + 120,
    }
    base.update(changes)
    return base


def make_verifier(keypairs, guard=None):
    return HumanJwtVerifier(
        issuer="https://idp.example.invalid/tenant",
        audience="clinic-api",
        trusted_keys=tuple(x[3] for x in keypairs),
        jti_validator=guard or SyntheticJtiGuard(),
        max_lifetime_seconds=300,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("key_index", [0, 1])
async def test_rs256_and_es256_validate_real_signature_claims_and_jti(keypairs, key_index):
    kid, alg, secret, _public = keypairs[key_index]
    guard = SyntheticJtiGuard()
    verifier = make_verifier(keypairs, guard)
    raw = jwt.encode(claims(), secret, algorithm=alg, headers={"kid": kid, "typ": "JWT"})
    principal = await verifier.verify(raw)
    assert principal.tenant_id == TENANT
    assert principal.principal_id == PRINCIPAL
    assert principal.jti == "synthetic-jti-001"
    assert guard.calls == [(TENANT, "synthetic-jti-001")]


@pytest.mark.asyncio
@pytest.mark.parametrize("overrides", [
    {"aud": "not-clinic-api"},
    {"iss": "https://evil.invalid/"},
    {"tenant_id": "invalid-uuid"},
    {"tenant_id": 123},
    {"tenant_id": None},
    {"tenant_id": "00000000-0000-0000-0000-000000000000"},
    {"sub": "not-an-account"},
    {"sub": ["uuid"]},
    {"jti": ""},
    {"exp": 0},
    {"nbf": int(time.time()) + 999},
    {"exp": int(time.time()) + 10000},
    {"iat": "not-a-number"},
])
async def test_bad_signed_claims_fail_closed(keypairs, overrides):
    kid, alg, secret, _public = keypairs[0]
    raw = jwt.encode(claims(**overrides), secret, algorithm=alg, headers={"kid": kid})
    with pytest.raises(AuthenticationRejected):
        await make_verifier(keypairs).verify(raw)


@pytest.mark.asyncio
async def test_unknown_kid_or_algorithm_confusion_rejected(keypairs):
    _kid, alg, secret, _public = keypairs[0]
    raw = jwt.encode(claims(), secret, algorithm=alg, headers={"kid": "unknown"})
    with pytest.raises(AuthenticationRejected):
        await make_verifier(keypairs).verify(raw)
    raw_hmac = jwt.encode(claims(), "attacker-known-secret", algorithm="HS256", headers={"kid": "rsa-a"})
    with pytest.raises(AuthenticationRejected):
        await make_verifier(keypairs).verify(raw_hmac)


@pytest.mark.asyncio
async def test_signature_invalid_and_revocation_unavailable_fail_closed(keypairs):
    kid, alg, _secret, _public = keypairs[0]
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    raw = jwt.encode(claims(), wrong_key, algorithm=alg, headers={"kid": kid})
    with pytest.raises(AuthenticationRejected):
        await make_verifier(keypairs).verify(raw)
    raw = jwt.encode(claims(), keypairs[0][2], algorithm=alg, headers={"kid": kid})
    with pytest.raises(AuthenticationRejected):
        await make_verifier(keypairs, SyntheticJtiGuard(reject=True)).verify(raw)


def test_invalid_config_no_revocation_or_wrong_key_algorithm(keypairs):
    with pytest.raises(ValueError):
        HumanJwtVerifier(
            issuer="issuer", audience="audience", trusted_keys=(keypairs[0][3],),
            jti_validator=None, max_lifetime_seconds=300,
        )
    with pytest.raises(ValueError):
        HumanJwtVerifier(
            issuer="issuer", audience="audience",
            trusted_keys=(keypairs[0][3], keypairs[0][3]),
            jti_validator=SyntheticJtiGuard(), max_lifetime_seconds=300,
        )
    with pytest.raises(ValueError):
        TrustedJwtPublicKey("mismatch", "ES256", keypairs[0][3].public_key_pem)


@pytest.mark.asyncio
async def test_unsigned_missing_and_client_supplied_context_rejected(keypairs):
    verifier = make_verifier(keypairs)
    with pytest.raises(AuthenticationRejected):
        await verifier.verify("")
    with pytest.raises(AuthenticationRejected):
        await verifier.verify("not-a.jwt.token")
    # No tenant_id request-path argument exists on the verifier API.


def test_human_jwt_verifier_rejects_subclass_and_bool_lifetime(keypairs):
    with pytest.raises(TypeError, match="cannot be subclassed"):
        class Evil(HumanJwtVerifier):  # type: ignore[misc]
            pass

    class PermitAllJti:
        async def ensure_active(self, *, tenant_id, token_jti):
            return None

    # A class name cannot be used as proof of revocation behavior.
    # A concrete authoritative store remains required at deployment.
    for invalid in (True, False, 3601):
        with pytest.raises(ValueError):
            HumanJwtVerifier(
                issuer="issuer", audience="audience",
                trusted_keys=(keypairs[0][3],),
                jti_validator=PermitAllJti(),
                max_lifetime_seconds=invalid,
            )
