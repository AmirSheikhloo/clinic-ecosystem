"""Exact pg_index catalog assertions for experimental generation indexes."""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg


class IndexCatalogError(RuntimeError):
    """Raised when an experimental index is missing, invalid, or mismatched."""


@dataclass(frozen=True)
class IndexCatalogRow:
    name: str
    table_name: str
    unique_index: bool
    valid: bool
    ready: bool
    definition: str
    oid: int


async def fetch_index(
    conn: asyncpg.Connection, index_name: str
) -> IndexCatalogRow | None:
    row = await conn.fetchrow(
        """
        SELECT c.relname AS name,
               t.relname AS table_name,
               i.indisunique AS unique_index,
               i.indisvalid AS valid,
               i.indisready AS ready,
               i.indexrelid AS oid,
               pg_get_indexdef(i.indexrelid) AS definition
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indexrelid
        JOIN pg_class t ON t.oid = i.indrelid
        WHERE c.relname = $1
        """,
        index_name,
    )
    if row is None:
        return None
    return IndexCatalogRow(
        name=row["name"],
        table_name=row["table_name"],
        unique_index=bool(row["unique_index"]),
        valid=bool(row["valid"]),
        ready=bool(row["ready"]),
        definition=row["definition"],
        oid=int(row["oid"]),
    )


async def assert_index_catalog(
    conn: asyncpg.Connection,
    *,
    index_name: str,
    table_name: str,
    required_fragments: list[str],
    forbidden_fragments: list[str] | None = None,
    unique: bool = True,
    valid: bool = True,
    ready: bool = True,
) -> IndexCatalogRow:
    row = await fetch_index(conn, index_name)
    if row is None:
        raise IndexCatalogError(f"missing index {index_name}")
    if row.table_name != table_name:
        raise IndexCatalogError(
            f"{index_name}: expected table {table_name}, got {row.table_name}"
        )
    if row.unique_index is not unique:
        raise IndexCatalogError(f"{index_name}: unique={row.unique_index}")
    if row.valid is not valid:
        raise IndexCatalogError(f"{index_name}: valid={row.valid}")
    if row.ready is not ready:
        raise IndexCatalogError(f"{index_name}: ready={row.ready}")
    for frag in required_fragments:
        if frag not in row.definition:
            raise IndexCatalogError(
                f"{index_name}: definition missing fragment {frag!r}: {row.definition}"
            )
    for frag in forbidden_fragments or []:
        if frag in row.definition:
            raise IndexCatalogError(
                f"{index_name}: definition unexpectedly contains {frag!r}"
            )
    return row
