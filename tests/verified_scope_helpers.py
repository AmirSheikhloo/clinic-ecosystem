"""TEST-ONLY mint of synthetic tenant scopes; never import from production code.

Python module visibility is not an unforgeable authentication boundary.
Application entrypoints must always call verified_jwt_transaction.
"""
from __future__ import annotations

from typing import Any
from clinic_ecosystem.infrastructure.persistence.authenticated_uow import (
    VerifiedTenantDbSession, _SCOPE_AUTH,
)
from clinic_ecosystem.shared_kernel.tenant_auth import VerifiedHumanPrincipal


def mint_verified_scope_for_tests(*, session: Any, principal: VerifiedHumanPrincipal):
    return VerifiedTenantDbSession(session=session, principal=principal, _auth=_SCOPE_AUTH)
