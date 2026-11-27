"""Patient operational notes, tags/alerts, and dossier finance hooks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from clinic_ecosystem.application.shared.errors import Conflict, NotFound, ValidationFailed
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import load_granted, require
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)
from clinic_ecosystem.presentation.http.scope_access import (
    filter_rows_by_scope,
    load_scopes,
    require_object_scope,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

router = APIRouter(prefix="/api/v1/patients", tags=["patient-ops"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


async def _ops_ready(uow: Uow) -> bool:
    row = await uow.session.execute(
        text("SELECT to_regclass('public.patient_operational_notes') IS NOT NULL AS ok")
    )
    return bool(row.mappings().one()["ok"])


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    department_id: UUID | None = None
    service_id: UUID | None = None


class NoteActionIn(BaseModel):
    action_kind: str = Field(pattern="^(PIN|UNPIN|RETRACT)$")
    reason: str = Field(min_length=1, max_length=200)


class TagAssignIn(BaseModel):
    tag_code: str = Field(min_length=1, max_length=64)
    tag_name: str | None = Field(default=None, max_length=100)
    department_id: UUID | None = None
    service_id: UUID | None = None


@router.get("/{patient_id}/notes")
async def list_notes(principal: Principal, uow: Uow, patient_id: UUID) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.PATIENTS_VIEW_PROFILE)
    scopes = await load_scopes(principal, uow, perm.PATIENTS_VIEW_PROFILE)
    if not scopes:
        return {"items": []}
    if not await _ops_ready(uow):
        raise Conflict("Ops notes schema unavailable", code="ops_schema_unavailable")
    result = await uow.session.execute(
        text(
            """
            SELECT n.id, n.body, n.department_id, n.service_id, n.created_at_utc,
                   n.created_by_user_id,
                   EXISTS (
                     SELECT 1 FROM patient_note_actions a
                     WHERE a.tenant_id = n.tenant_id AND a.note_id = n.id
                       AND a.action_kind = 'PIN'
                       AND NOT EXISTS (
                         SELECT 1 FROM patient_note_actions u
                         WHERE u.tenant_id = a.tenant_id AND u.note_id = a.note_id
                           AND u.action_kind = 'UNPIN' AND u.created_at_utc > a.created_at_utc
                       )
                   ) AS pinned,
                   EXISTS (
                     SELECT 1 FROM patient_note_actions a
                     WHERE a.tenant_id = n.tenant_id AND a.note_id = n.id
                       AND a.action_kind = 'RETRACT'
                   ) AS retracted
            FROM patient_operational_notes n
            WHERE n.tenant_id = :tenant_id AND n.patient_id = :patient_id
            ORDER BY n.created_at_utc DESC, n.id DESC
            LIMIT 100
            """
        ),
        {"tenant_id": principal.claims.tenant_id, "patient_id": patient_id},
    )
    raw = [dict(r) for r in result.mappings().all() if not r["retracted"]]
    scoped = filter_rows_by_scope(scopes, raw)
    return {
        "items": [
            {
                "id": str(r["id"]),
                "body": r["body"],
                "department_id": str(r["department_id"]) if r["department_id"] else None,
                "service_id": str(r["service_id"]) if r["service_id"] else None,
                "created_at_utc": r["created_at_utc"].isoformat(),
                "pinned": bool(r["pinned"]),
                "retracted": bool(r["retracted"]),
            }
            for r in scoped
        ]
    }


@router.post("/{patient_id}/notes")
async def create_note(
    principal: Principal, uow: Uow, patient_id: UUID, body: NoteIn
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.PATIENTS_UPDATE)
    scopes = await load_scopes(principal, uow, perm.PATIENTS_UPDATE)
    require_object_scope(
        scopes, department_id=body.department_id, service_id=body.service_id
    )
    if not await _ops_ready(uow):
        raise Conflict("Ops notes schema unavailable", code="ops_schema_unavailable")
    if not body.body.strip():
        raise ValidationFailed("Note body required", code="empty_note")
    now = datetime.now(timezone.utc)
    note_id = new_uuid7()
    await uow.session.execute(
        text(
            """
            INSERT INTO patient_operational_notes (
              id, tenant_id, patient_id, department_id, service_id, body,
              created_by_user_id, created_at_utc
            ) VALUES (:id, :tenant_id, :patient_id, :dept, :service_id, :body, :user_id, :now)
            """
        ),
        {
            "id": note_id,
            "tenant_id": principal.claims.tenant_id,
            "patient_id": patient_id,
            "dept": body.department_id,
            "service_id": body.service_id,
            "body": body.body.strip(),
            "user_id": principal.account.id,
            "now": now,
        },
    )
    await SqlAuditStore(uow.session).append(
        tenant_id=principal.claims.tenant_id,
        actor_type="USER_ACCOUNT",
        actor_id=principal.account.id,
        operation="patient.note_created",
        target_type="patient",
        target_id=patient_id,
        details={"note_id": str(note_id)},
    )
    await uow.commit()
    return {"id": str(note_id)}


@router.post("/{patient_id}/notes/{note_id}/actions")
async def note_action(
    principal: Principal,
    uow: Uow,
    patient_id: UUID,
    note_id: UUID,
    body: NoteActionIn,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.PATIENTS_UPDATE)
    scopes = await load_scopes(principal, uow, perm.PATIENTS_UPDATE)
    if not await _ops_ready(uow):
        raise Conflict("Ops notes schema unavailable", code="ops_schema_unavailable")
    exists = await uow.session.execute(
        text(
            """
            SELECT id, department_id, service_id FROM patient_operational_notes
            WHERE tenant_id = :tenant_id AND patient_id = :patient_id AND id = :note_id
            """
        ),
        {
            "tenant_id": principal.claims.tenant_id,
            "patient_id": patient_id,
            "note_id": note_id,
        },
    )
    note_row = exists.mappings().one_or_none()
    if note_row is None:
        raise NotFound("Note not found", code="note_not_found")
    require_object_scope(
        scopes,
        department_id=note_row["department_id"],
        service_id=note_row["service_id"],
    )
    now = datetime.now(timezone.utc)
    await uow.session.execute(
        text(
            """
            INSERT INTO patient_note_actions (
              id, tenant_id, note_id, action_kind, reason, operator_user_id, created_at_utc
            ) VALUES (:id, :tenant_id, :note_id, :kind, :reason, :user_id, :now)
            """
        ),
        {
            "id": new_uuid7(),
            "tenant_id": principal.claims.tenant_id,
            "note_id": note_id,
            "kind": body.action_kind,
            "reason": body.reason.strip(),
            "user_id": principal.account.id,
            "now": now,
        },
    )
    await uow.commit()
    return {"note_id": str(note_id), "action_kind": body.action_kind}


@router.get("/{patient_id}/tags")
async def list_tags(principal: Principal, uow: Uow, patient_id: UUID) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.PATIENTS_VIEW_PROFILE)
    scopes = await load_scopes(principal, uow, perm.PATIENTS_VIEW_PROFILE)
    if not scopes:
        return {"items": []}
    if not await _ops_ready(uow):
        raise Conflict("Ops tags schema unavailable", code="ops_schema_unavailable")
    result = await uow.session.execute(
        text(
            """
            SELECT t.id, c.tag_code, c.tag_name, t.created_at_utc,
                   t.department_id, t.service_id
            FROM patient_staff_tags t
            JOIN staff_tag_catalog c ON c.tenant_id = t.tenant_id AND c.id = t.tag_id
            WHERE t.tenant_id = :tenant_id AND t.patient_id = :patient_id
              AND t.removed_at_utc IS NULL
            ORDER BY c.tag_code
            """
        ),
        {"tenant_id": principal.claims.tenant_id, "patient_id": patient_id},
    )
    raw = [dict(r) for r in result.mappings().all()]
    scoped = filter_rows_by_scope(scopes, raw)
    return {
        "items": [
            {
                "id": str(r["id"]),
                "tag_code": r["tag_code"],
                "tag_name": r["tag_name"],
                "created_at_utc": r["created_at_utc"].isoformat(),
            }
            for r in scoped
        ]
    }


@router.post("/{patient_id}/tags")
async def assign_tag(
    principal: Principal, uow: Uow, patient_id: UUID, body: TagAssignIn
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.PATIENTS_UPDATE)
    scopes = await load_scopes(principal, uow, perm.PATIENTS_UPDATE)
    require_object_scope(
        scopes, department_id=body.department_id, service_id=body.service_id
    )
    if not await _ops_ready(uow):
        raise Conflict("Ops tags schema unavailable", code="ops_schema_unavailable")
    now = datetime.now(timezone.utc)
    tag_id = await uow.session.execute(
        text(
            """
            SELECT id FROM staff_tag_catalog
            WHERE tenant_id = :tenant_id AND tag_code = :code
            """
        ),
        {"tenant_id": principal.claims.tenant_id, "code": body.tag_code},
    )
    row = tag_id.mappings().one_or_none()
    if row is None:
        new_tag = new_uuid7()
        await uow.session.execute(
            text(
                """
                INSERT INTO staff_tag_catalog (
                  id, tenant_id, tag_code, tag_name, is_active, created_at_utc, updated_at_utc
                ) VALUES (:id, :tenant_id, :code, :name, TRUE, :now, :now)
                """
            ),
            {
                "id": new_tag,
                "tenant_id": principal.claims.tenant_id,
                "code": body.tag_code,
                "name": (body.tag_name or body.tag_code).strip(),
                "now": now,
            },
        )
        catalog_id = new_tag
    else:
        catalog_id = row["id"]
    assign_id = new_uuid7()
    await uow.session.execute(
        text(
            """
            INSERT INTO patient_staff_tags (
              id, tenant_id, patient_id, tag_id, department_id, service_id,
              created_by_user_id, created_at_utc
            ) VALUES (:id, :tenant_id, :patient_id, :tag_id, :dept, :service_id, :user_id, :now)
            """
        ),
        {
            "id": assign_id,
            "tenant_id": principal.claims.tenant_id,
            "patient_id": patient_id,
            "tag_id": catalog_id,
            "dept": body.department_id,
            "service_id": body.service_id,
            "user_id": principal.account.id,
            "now": now,
        },
    )
    await uow.commit()
    return {"id": str(assign_id), "tag_code": body.tag_code}


@router.delete("/{patient_id}/tags/{assignment_id}")
async def remove_tag(
    principal: Principal,
    uow: Uow,
    patient_id: UUID,
    assignment_id: UUID,
    reason: Annotated[str, Query(min_length=1, max_length=200)] = "removed",
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.PATIENTS_UPDATE)
    now = datetime.now(timezone.utc)
    result = await uow.session.execute(
        text(
            """
            UPDATE patient_staff_tags SET
              removed_at_utc = :now,
              removed_by_user_id = :user_id,
              removal_reason = :reason
            WHERE tenant_id = :tenant_id AND patient_id = :patient_id AND id = :id
              AND removed_at_utc IS NULL
            RETURNING id
            """
        ),
        {
            "now": now,
            "user_id": principal.account.id,
            "reason": reason,
            "tenant_id": principal.claims.tenant_id,
            "patient_id": patient_id,
            "id": assignment_id,
        },
    )
    if result.mappings().one_or_none() is None:
        raise NotFound("Tag assignment not found", code="tag_not_found")
    await uow.commit()
    return {"id": str(assignment_id), "removed": True}
