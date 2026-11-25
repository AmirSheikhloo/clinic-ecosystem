"""Small SQL helpers shared by persistence adapters."""

from __future__ import annotations


def like_contains(term: str) -> str:
    """Escape LIKE metacharacters and wrap for a contains match (ESCAPE '\\')."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
