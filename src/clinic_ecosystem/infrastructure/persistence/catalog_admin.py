"""Manager-only catalog administration queries (Workstream E)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.infrastructure.persistence.sql_helpers import like_contains

_SERVICE_COLS = (
    "s.id AS service_id, s.service_code, s.service_name, s.default_duration_minutes, "
    "s.default_price_irr, s.is_active, s.aggregate_version, s.created_at_utc, s.updated_at_utc"
)


class SqlCatalogAdmin:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_namespace(self, tenant_id: UUID) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"{tenant_id}:catalog"},
        )

    # services -------------------------------------------------------------

    async def list_services(
        self, *, tenant_id: UUID, q: str | None, is_active: bool | None, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        where = ["s.tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}
        if q:
            where.append("(s.service_name ILIKE :pat ESCAPE '\\' OR s.service_code ILIKE :pat ESCAPE '\\')")
            params["pat"] = like_contains(q)
        if is_active is not None:
            where.append("s.is_active = :is_active")
            params["is_active"] = is_active
        clause = " AND ".join(where)
        total = await self._session.execute(
            text(f"SELECT count(*) FROM services s WHERE {clause}"), params
        )
        rows = await self._session.execute(
            text(
                f"""
                SELECT {_SERVICE_COLS},
                       (SELECT count(*) FROM service_resource_requirements r
                        WHERE r.tenant_id = s.tenant_id AND r.service_id = s.id)
                           AS requirement_count
                FROM services s WHERE {clause}
                ORDER BY s.service_name, s.id LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        return [dict(r._mapping) for r in rows], int(total.scalar_one())

    async def get_service(
        self, *, tenant_id: UUID, service_id: UUID, for_update: bool = False
    ) -> dict[str, Any] | None:
        result = await self._session.execute(
            text(
                f"SELECT {_SERVICE_COLS} FROM services s "
                "WHERE s.tenant_id = :tenant_id AND s.id = :id"
                + (" FOR UPDATE" if for_update else "")
            ),
            {"tenant_id": tenant_id, "id": service_id},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def code_in_use(
        self, *, tenant_id: UUID, code: str, exclude_id: UUID | None
    ) -> bool:
        result = await self._session.execute(
            text(
                "SELECT 1 FROM services WHERE tenant_id = :t AND lower(service_code) = lower(:c) "
                "AND (CAST(:x AS uuid) IS NULL OR id <> CAST(:x AS uuid)) LIMIT 1"
            ),
            {"t": tenant_id, "c": code, "x": exclude_id},
        )
        return result.first() is not None

    async def insert_service(
        self, *, tenant_id: UUID, service_id: UUID, code: str | None, name: str,
        duration: int, price: int, now: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO services (id, tenant_id, service_code, service_name,
                    default_duration_minutes, default_price_irr, is_active,
                    aggregate_version, created_at_utc, updated_at_utc)
                VALUES (:id, :t, :code, :name, :dur, :price, TRUE, 1, :now, :now)
                """
            ),
            {"id": service_id, "t": tenant_id, "code": code, "name": name,
             "dur": duration, "price": price, "now": now},
        )

    async def update_service_cas(
        self, *, tenant_id: UUID, service_id: UUID, expected_version: int,
        fields: dict[str, Any], now: datetime,
    ) -> int | None:
        columns = {
            "service_code": "service_code",
            "service_name": "service_name",
            "default_duration_minutes": "default_duration_minutes",
            "default_price_irr": "default_price_irr",
            "is_active": "is_active",
        }
        sets = ["aggregate_version = aggregate_version + 1", "updated_at_utc = :now"]
        params: dict[str, Any] = {"t": tenant_id, "id": service_id, "exp": expected_version, "now": now}
        for key, column in columns.items():
            if key in fields:
                sets.append(f"{column} = :{key}")
                params[key] = fields[key]
        result = await self._session.execute(
            text(
                f"UPDATE services SET {', '.join(sets)} WHERE tenant_id = :t AND id = :id "
                "AND aggregate_version = :exp RETURNING aggregate_version"
            ),
            params,
        )
        row = result.first()
        return int(row.aggregate_version) if row else None

    async def list_requirements(self, *, tenant_id: UUID, service_id: UUID) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT r.id AS requirement_id, r.requirement_group, r.required_resource_type,
                       r.specific_resource_id, br.resource_name AS specific_resource_name,
                       r.quantity_required
                FROM service_resource_requirements r
                LEFT JOIN bookable_resources br
                  ON br.tenant_id = r.tenant_id AND br.id = r.specific_resource_id
                WHERE r.tenant_id = :t AND r.service_id = :s
                ORDER BY r.requirement_group, r.id
                """
            ),
            {"t": tenant_id, "s": service_id},
        )
        return [dict(r._mapping) for r in result]

    async def replace_requirements(
        self, *, tenant_id: UUID, service_id: UUID, items: list[dict[str, Any]],
        ids: list[UUID], now: datetime,
    ) -> None:
        await self._session.execute(
            text("DELETE FROM service_resource_requirements WHERE tenant_id = :t AND service_id = :s"),
            {"t": tenant_id, "s": service_id},
        )
        for new_id, item in zip(ids, items, strict=True):
            await self._session.execute(
                text(
                    """
                    INSERT INTO service_resource_requirements (
                        id, tenant_id, service_id, requirement_group, required_resource_type,
                        specific_resource_id, quantity_required, created_at_utc
                    ) VALUES (:id, :t, :s, :grp, :rtype, :specific, :qty, :now)
                    """
                ),
                {"id": new_id, "t": tenant_id, "s": service_id, "grp": item["requirement_group"],
                 "rtype": item["required_resource_type"],
                 "specific": item.get("specific_resource_id"),
                 "qty": item["quantity_required"], "now": now},
            )

    # resources ------------------------------------------------------------

    async def list_resources(
        self, *, tenant_id: UUID, q: str | None, resource_type: str | None,
        is_active: bool | None, limit: int, offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        where = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}
        if q:
            where.append("resource_name ILIKE :pat ESCAPE '\\'")
            params["pat"] = like_contains(q)
        if resource_type:
            where.append("resource_type = :rtype")
            params["rtype"] = resource_type
        if is_active is not None:
            where.append("is_active = :is_active")
            params["is_active"] = is_active
        clause = " AND ".join(where)
        total = await self._session.execute(
            text(f"SELECT count(*) FROM bookable_resources WHERE {clause}"), params
        )
        rows = await self._session.execute(
            text(
                f"SELECT id AS resource_id, resource_type, resource_name, is_active, created_at_utc "
                f"FROM bookable_resources WHERE {clause} "
                "ORDER BY resource_name, id LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [dict(r._mapping) for r in rows], int(total.scalar_one())

    async def get_resource(
        self, *, tenant_id: UUID, resource_id: UUID, for_update: bool = False
    ) -> dict[str, Any] | None:
        result = await self._session.execute(
            text(
                "SELECT id AS resource_id, resource_type, resource_name, is_active, created_at_utc "
                "FROM bookable_resources WHERE tenant_id = :t AND id = :id"
                + (" FOR UPDATE" if for_update else "")
            ),
            {"t": tenant_id, "id": resource_id},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def insert_resource(
        self, *, tenant_id: UUID, resource_id: UUID, resource_type: str, name: str, now: datetime
    ) -> None:
        await self._session.execute(
            text(
                "INSERT INTO bookable_resources (id, tenant_id, resource_type, resource_name, "
                "is_active, created_at_utc) VALUES (:id, :t, :rtype, :name, TRUE, :now)"
            ),
            {"id": resource_id, "t": tenant_id, "rtype": resource_type, "name": name, "now": now},
        )

    async def update_resource(
        self, *, tenant_id: UUID, resource_id: UUID, name: str | None, is_active: bool | None
    ) -> None:
        sets, params = [], {"t": tenant_id, "id": resource_id}
        if name is not None:
            sets.append("resource_name = :name")
            params["name"] = name
        if is_active is not None:
            sets.append("is_active = :active")
            params["active"] = is_active
        if sets:
            await self._session.execute(
                text(f"UPDATE bookable_resources SET {', '.join(sets)} WHERE tenant_id = :t AND id = :id"),
                params,
            )

    async def future_allocation_count(
        self, *, tenant_id: UUID, resource_id: UUID, now: datetime
    ) -> int:
        result = await self._session.execute(
            text(
                """
                SELECT count(*) FROM appointment_resource_allocations
                WHERE tenant_id = :t AND resource_id = :r
                  AND allocation_status IN ('PENDING_PAYMENT_HOLD','CONFIRMED','CHECKED_IN')
                  AND upper(time_slot) > :now
                """
            ),
            {"t": tenant_id, "r": resource_id, "now": now},
        )
        return int(result.scalar_one())
