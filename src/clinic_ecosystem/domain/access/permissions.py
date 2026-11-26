"""Permission catalog for the synthetic BETA-02 operations increment.

Codes prefixed ``BETA02_`` and ``BETA01B_`` are provisional, non-production
catalog entries (see docs/architecture_change_records/ACR-BETA02-001). They are
enforced server-side only; the browser may use the same codes for display
gating but never as an authority.
"""

from __future__ import annotations

from dataclasses import dataclass

CATALOG_SERVICES_READ = "CATALOG_SERVICES_READ"
ALLOW_MANUAL_OVERBOOKING = "ALLOW_MANUAL_OVERBOOKING"

PATIENTS_REGISTER = "BETA01B_PATIENTS_REGISTER"
PATIENTS_SEARCH = "BETA01B_PATIENTS_SEARCH"
CATALOG_RESOURCES_READ = "BETA01B_CATALOG_RESOURCES_READ"
APPOINTMENTS_SCHEDULE_MANUAL = "BETA01B_APPOINTMENTS_SCHEDULE_MANUAL"
APPOINTMENTS_LIST = "BETA01B_APPOINTMENTS_LIST"

PATIENTS_VIEW_PROFILE = "BETA02_PATIENTS_VIEW_PROFILE"
PATIENTS_UPDATE = "BETA02_PATIENTS_UPDATE"
PATIENTS_SET_ACTIVE = "BETA02_PATIENTS_SET_ACTIVE"
PATIENTS_VIEW_HISTORY = "BETA02_PATIENTS_VIEW_HISTORY"

STAFF_VIEW = "BETA02_STAFF_VIEW"
STAFF_MANAGE = "BETA02_STAFF_MANAGE"
STAFF_PROVISION_LOGIN = "BETA02_STAFF_PROVISION_LOGIN"

ACCOUNTS_VIEW = "BETA02_ACCOUNTS_VIEW"
ACCOUNTS_SET_ACTIVE = "BETA02_ACCOUNTS_SET_ACTIVE"

ROLES_VIEW = "BETA02_ROLES_VIEW"
ROLES_MANAGE = "BETA02_ROLES_MANAGE"
USER_ROLES_ASSIGN = "BETA02_USER_ROLES_ASSIGN"
GOVERNANCE_VIEW = "BETA02_GOVERNANCE_VIEW"
GOVERNANCE_MANAGE = "BETA02_GOVERNANCE_MANAGE"

CATALOG_SERVICES_MANAGE = "BETA02_CATALOG_SERVICES_MANAGE"
CATALOG_RESOURCES_MANAGE = "BETA02_CATALOG_RESOURCES_MANAGE"

APPOINTMENTS_VIEW_DETAILS = "BETA02_APPOINTMENTS_VIEW_DETAILS"
APPOINTMENTS_CANCEL = "BETA02_APPOINTMENTS_CANCEL"
APPOINTMENTS_RESCHEDULE = "BETA02_APPOINTMENTS_RESCHEDULE"
APPOINTMENTS_CHECK_IN = "BETA02_APPOINTMENTS_CHECK_IN"
APPOINTMENTS_COMPLETE = "BETA02_APPOINTMENTS_COMPLETE"
APPOINTMENTS_MARK_NO_SHOW = "BETA02_APPOINTMENTS_MARK_NO_SHOW"


@dataclass(frozen=True, slots=True)
class PermissionDefinition:
    code: str
    category: str
    label_fa: str
    description: str


_DEFS: tuple[PermissionDefinition, ...] = (
    PermissionDefinition(PATIENTS_SEARCH, "patients", "جست‌وجوی بیماران", "Search and list patients"),
    PermissionDefinition(PATIENTS_REGISTER, "patients", "ثبت بیمار جدید", "Register a patient"),
    PermissionDefinition(PATIENTS_VIEW_PROFILE, "patients", "مشاهده پرونده بیمار", "View patient profile"),
    PermissionDefinition(PATIENTS_UPDATE, "patients", "ویرایش مشخصات بیمار", "Update patient profile fields"),
    PermissionDefinition(PATIENTS_SET_ACTIVE, "patients", "فعال/غیرفعال کردن بیمار", "Activate or deactivate patient"),
    PermissionDefinition(PATIENTS_VIEW_HISTORY, "patients", "مشاهده سوابق نوبت بیمار", "View patient appointment history"),
    PermissionDefinition(STAFF_VIEW, "staff", "مشاهده کارکنان", "View staff directory"),
    PermissionDefinition(STAFF_MANAGE, "staff", "مدیریت کارکنان", "Create, edit and activate staff profiles"),
    PermissionDefinition(STAFF_PROVISION_LOGIN, "staff", "ایجاد حساب ورود", "Provision an optional login account"),
    PermissionDefinition(ACCOUNTS_VIEW, "access", "مشاهده حساب‌های کاربری", "View login accounts"),
    PermissionDefinition(ACCOUNTS_SET_ACTIVE, "access", "تعلیق/فعال‌سازی حساب", "Suspend or reactivate login accounts"),
    PermissionDefinition(ROLES_VIEW, "access", "مشاهده نقش‌ها", "View roles and effective permissions"),
    PermissionDefinition(ROLES_MANAGE, "access", "مدیریت نقش‌ها", "Create roles and assign role permissions"),
    PermissionDefinition(USER_ROLES_ASSIGN, "access", "تخصیص نقش به کاربر", "Assign roles to accounts"),
    PermissionDefinition(GOVERNANCE_VIEW, "access", "مشاهده سطوح مدیریتی", "View governance assignments"),
    PermissionDefinition(GOVERNANCE_MANAGE, "access", "مدیریت سطوح مدیریتی", "Assign governance roles"),
    PermissionDefinition(CATALOG_SERVICES_READ, "catalog", "مشاهده خدمات", "Read active services"),
    PermissionDefinition(CATALOG_RESOURCES_READ, "catalog", "مشاهده منابع", "Read active resources"),
    PermissionDefinition(CATALOG_SERVICES_MANAGE, "catalog", "مدیریت خدمات", "Create and edit services"),
    PermissionDefinition(CATALOG_RESOURCES_MANAGE, "catalog", "مدیریت منابع", "Create and edit resources"),
    PermissionDefinition(APPOINTMENTS_LIST, "appointments", "مشاهده تقویم نوبت‌ها", "List appointments"),
    PermissionDefinition(APPOINTMENTS_VIEW_DETAILS, "appointments", "جزئیات نوبت", "View appointment details"),
    PermissionDefinition(APPOINTMENTS_SCHEDULE_MANUAL, "appointments", "ثبت نوبت دستی", "Schedule manual appointments"),
    PermissionDefinition(ALLOW_MANUAL_OVERBOOKING, "appointments", "تأیید هم‌پوشانی دستی", "Acknowledge manual overlaps"),
    PermissionDefinition(APPOINTMENTS_CANCEL, "appointments", "لغو نوبت", "Cancel manual appointments"),
    PermissionDefinition(APPOINTMENTS_RESCHEDULE, "appointments", "جابه‌جایی نوبت", "Reschedule manual appointments"),
    PermissionDefinition(APPOINTMENTS_CHECK_IN, "appointments", "ثبت حضور", "Check in a confirmed appointment"),
    PermissionDefinition(APPOINTMENTS_COMPLETE, "appointments", "اتمام نوبت", "Mark a checked-in appointment completed"),
    PermissionDefinition(
        APPOINTMENTS_MARK_NO_SHOW, "appointments", "ثبت عدم حضور", "Mark a confirmed appointment as no-show"
    ),
)

PERMISSION_CATALOG: dict[str, PermissionDefinition] = {d.code: d for d in _DEFS}
