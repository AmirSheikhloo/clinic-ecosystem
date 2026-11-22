"""JWT trust boundary for Tenant Plane (frozen spec clauses 246-248, 747-749).

No caller-supplied tenant path, JSON or custom PostgreSQL GUC is considered
authoritative. Signed human JWTs only; Sync Ed25519 and internal jobs are
separate authentication paths and are NOT accepted by this verifier.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jwt.exceptions import InvalidTokenError


class AuthenticationRejected(PermissionError):
    """Do not disclose token internals, claims or key material to a caller."""


@dataclass(frozen=True)
class TrustedJwtPublicKey:
    kid: str
    algorithm: Literal["RS256", "ES256"]
    public_key_pem: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.kid, str) or not self.kid or len(self.kid) > 128:
            raise ValueError("invalid configured signing-key identifier")
        if self.algorithm not in ("RS256", "ES256"):
            raise ValueError("only the deployed RS256/ES256 key policy is allowed")
        if not isinstance(self.public_key_pem, bytes):
            raise TypeError("signing verification key must be PEM bytes")
        key = serialization.load_pem_public_key(self.public_key_pem)
        if self.algorithm == "RS256":
            if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 2048:
                raise ValueError("RS256 requires an RSA public key >=2048 bits")
        elif not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(
            key.curve, ec.SECP256R1
        ):
            raise ValueError("ES256 requires an EC P-256 public key")


class JwtJtiValidator(Protocol):
    async def ensure_active(self, *, tenant_id: UUID, token_jti: str) -> None:
        """Reject revoked, unknown or replay-ineligible JWT identifiers.

        Must be backed by the approved authoritative token lifecycle store;
        a permit-all checker is NOT a production implementation.
        """


@dataclass(frozen=True)
class VerifiedHumanPrincipal:
    """Produced by a successful server verification, not from a user payload."""
    tenant_id: UUID
    person_id: UUID
    jti: str
    issued_at_unix: int
    expires_at_unix: int

    # This value alone is not an unforgeable capability inside Python;
    # only a trusted application entrypoint may call the verifier and then
    # bind this context to a DB transaction.


class HumanJwtVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        trusted_keys: tuple[TrustedJwtPublicKey, ...],
        jti_validator: JwtJtiValidator,
        max_lifetime_seconds: int,
    ) -> None:
        if not issuer or not audience or not trusted_keys:
            raise ValueError("issuer, audience and at least one signing key are mandatory")
        if not isinstance(max_lifetime_seconds, int) or max_lifetime_seconds < 1:
            raise ValueError("short-lived token policy must be configured explicitly")
        if jti_validator is None or not callable(getattr(jti_validator, "ensure_active", None)):
            raise ValueError("authoritative jti/revocation validation is mandatory")
        keyed = {key.kid: key for key in trusted_keys}
        if len(keyed) != len(trusted_keys):
            raise ValueError("duplicate signing-key kid")
        self._keys = keyed
        self._issuer = issuer
        self._audience = audience
        self._jti_validator = jti_validator
        self._max_lifetime = max_lifetime_seconds

    async def verify(self, raw_token: str) -> VerifiedHumanPrincipal:
        if not isinstance(raw_token, str) or not raw_token or len(raw_token) > 16384:
            raise AuthenticationRejected("token rejected")
        try:
            header = jwt.get_unverified_header(raw_token)
            if header.get("typ", "JWT") != "JWT" or "crit" in header:
                raise AuthenticationRejected("token rejected")
            kid = header.get("kid")
            algorithm = header.get("alg")
            if not isinstance(kid, str) or kid not in self._keys:
                raise AuthenticationRejected("token rejected")
            trusted = self._keys[kid]
            if algorithm != trusted.algorithm:
                raise AuthenticationRejected("token rejected")
            claims = jwt.decode(
                raw_token,
                key=trusted.public_key_pem,
                algorithms=[trusted.algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options={
                    "require": [
                        "exp", "nbf", "iat", "aud", "iss", "jti",
                        "sub", "tenant_id"
                    ],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                },
                leeway=0,
            )
            if any(type(claims.get(k)) is not int for k in ("iat", "nbf", "exp")):
                raise AuthenticationRejected("token rejected")
            if claims["nbf"] > claims["exp"] or claims["iat"] > claims["exp"]:
                raise AuthenticationRejected("token rejected")
            if claims["exp"] - claims["iat"] > self._max_lifetime:
                raise AuthenticationRejected("token rejected")
            if not isinstance(claims["jti"], str) or not 1 <= len(claims["jti"]) <= 256:
                raise AuthenticationRejected("token rejected")
            tenant = UUID(claims["tenant_id"])
            subject = UUID(claims["sub"])
            if tenant.int == 0 or subject.int == 0:
                raise AuthenticationRejected("token rejected")
            # No exception is swallowed: unavailable revocation store denies access.
            await self._jti_validator.ensure_active(
                tenant_id=tenant, token_jti=claims["jti"]
            )
            return VerifiedHumanPrincipal(
                tenant_id=tenant,
                person_id=subject,
                jti=claims["jti"],
                issued_at_unix=claims["iat"],
                expires_at_unix=claims["exp"],
            )
        except (InvalidTokenError, ValueError, TypeError, KeyError) as exc:
            raise AuthenticationRejected("token rejected") from exc
