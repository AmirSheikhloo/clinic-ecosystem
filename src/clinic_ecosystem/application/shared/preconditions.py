"""If-Match / expected aggregate_version parsing (clauses 121-135)."""

from __future__ import annotations

import re

from clinic_ecosystem.application.shared.errors import PreconditionRequired, ValidationFailed

_ETAG = re.compile(r'^(?:W/)?"?(\d{1,18})"?$')


def parse_if_match(header: str | None) -> int:
    if header is None or not header.strip():
        raise PreconditionRequired("If-Match header with the current version is required")
    match = _ETAG.match(header.strip())
    if not match:
        raise ValidationFailed("If-Match must carry a numeric version", code="if_match_invalid")
    return int(match.group(1))


def etag(version: int) -> str:
    return f'"{version}"'
