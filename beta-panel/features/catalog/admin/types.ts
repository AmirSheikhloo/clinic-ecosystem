export type ServiceAdminRow = {
  service_id: string;
  service_code: string | null;
  service_name: string;
  default_duration_minutes: number;
  default_price_irr: number;
  is_active: boolean;
  aggregate_version: number;
  requirement_count?: number;
};

export type RequirementRow = {
  requirement_id?: string;
  requirement_group: string;
  required_resource_type: string;
  specific_resource_id: string | null;
  specific_resource_name?: string | null;
  quantity_required: number;
};

export type ServiceDetail = ServiceAdminRow & { requirements: RequirementRow[] };

export type ResourceAdminRow = {
  resource_id: string;
  resource_type: string;
  resource_name: string;
  is_active: boolean;
};

export const RESOURCE_TYPE_LABEL: Record<string, string> = {
  PRACTITIONER: "ارائه‌دهنده",
  ROOM: "اتاق",
  DEVICE: "دستگاه",
};

export const RESOURCE_TYPES = Object.keys(RESOURCE_TYPE_LABEL);

export const ADMIN_PAGE_SIZE = 25;

export function parseWholeNumber(raw: string): number | null {
  const text = raw.trim();
  if (!/^\d{1,12}$/.test(text)) return null;
  return Number(text);
}
