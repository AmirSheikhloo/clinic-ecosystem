export type PermissionDef = { code: string; category: string; label_fa: string; description: string };

export type PermissionCatalog = { items: PermissionDef[]; governance_roles: string[] };

export type RoleRow = {
  role_id: string;
  role_code: string;
  role_name: string;
  is_system_defined: boolean;
  permissions: string[];
  member_count: number;
};

export type AccountRow = {
  account_id: string;
  person_id: string;
  first_name: string;
  last_name: string;
  login_identifier: string;
  is_active: boolean;
  is_locked: boolean;
  staff_kind: string | null;
  roles: string[];
  governance_roles: string[];
  aggregate_version: number;
};

export type GovernanceRow = { person_id: string; first_name: string; last_name: string; roles: string[] };

export type EffectivePermission = { permission_code: string; via_roles: string[] };

export const CATEGORY_LABEL: Record<string, string> = {
  patients: "بیماران",
  staff: "کارکنان",
  access: "کاربران و دسترسی",
  appointments: "نوبت‌ها",
  catalog: "خدمات و منابع",
};

export const GOVERNANCE_LABEL: Record<string, string> = {
  CLINIC_OWNER: "مالک کلینیک",
  CLINIC_MANAGER: "مدیر کلینیک",
  DEPUTY_ADMIN: "معاون مدیر",
  RECEPTIONIST: "پذیرش",
};

export const ACCOUNT_PAGE_SIZE = 25;

export function governanceLabel(code: string): string {
  return GOVERNANCE_LABEL[code] ?? code;
}

export function groupByCategory(items: PermissionDef[]): Array<[string, PermissionDef[]]> {
  const groups = new Map<string, PermissionDef[]>();
  for (const item of items) {
    const list = groups.get(item.category) ?? [];
    list.push(item);
    groups.set(item.category, list);
  }
  return Array.from(groups.entries());
}

export function toggleInSet<T>(current: readonly T[], value: T, on: boolean): T[] {
  const next = new Set(current);
  if (on) next.add(value);
  else next.delete(value);
  return Array.from(next);
}

export function accountDisplayName(account: Pick<AccountRow, "first_name" | "last_name" | "login_identifier">): string {
  const name = `${account.first_name} ${account.last_name}`.trim();
  return name || account.login_identifier;
}
