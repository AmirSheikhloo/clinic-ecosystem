/** Client-side helpers to mirror backend resource requirement matching. */

export const RESOURCE_TYPE_LABEL: Record<string, string> = {
  PRACTITIONER: "ارائه‌دهنده",
  ROOM: "اتاق",
  DEVICE: "دستگاه",
};

export function resourceTypeLabel(type: string): string {
  return RESOURCE_TYPE_LABEL[type] ?? type;
}

export type Resource = {
  id: string;
  resource_type: string;
  resource_name: string;
  is_active: boolean;
};

export type Requirement = {
  id: string;
  requirement_group: string;
  required_resource_type: string;
  specific_resource_id: string | null;
  quantity_required: number;
};

export type SelectionIssue =
  | { ok: true }
  | { ok: false; code: "insufficient" | "extra" | "empty_required"; message: string };

export function validateResourceSelection(
  requirements: Requirement[],
  selectedIds: string[],
  resourcesById: Map<string, Resource>,
): SelectionIssue {
  const unique = Array.from(new Set(selectedIds));
  if (unique.length !== selectedIds.length) {
    return { ok: false, code: "extra", message: "منبع تکراری انتخاب شده است" };
  }
  if (!requirements.length) {
    if (!unique.length) {
      return {
        ok: false,
        code: "empty_required",
        message: "حداقل یک منبع فعال باید انتخاب شود",
      };
    }
    for (const id of unique) {
      if (!resourcesById.get(id)?.is_active) {
        return { ok: false, code: "insufficient", message: "منبع نامعتبر انتخاب شده است" };
      }
    }
    return { ok: true };
  }

  const remaining = [...unique];
  for (const req of requirements) {
    const matched: string[] = [];
    for (const id of [...remaining]) {
      const resource = resourcesById.get(id);
      if (!resource || !resource.is_active) continue;
      if (req.specific_resource_id && id !== req.specific_resource_id) continue;
      if (resource.resource_type !== req.required_resource_type) continue;
      matched.push(id);
      remaining.splice(remaining.indexOf(id), 1);
      if (matched.length === req.quantity_required) break;
    }
    if (matched.length < req.quantity_required) {
      return {
        ok: false,
        code: "insufficient",
        message: `الزام گروه «${req.requirement_group}» برآورده نشده است`,
      };
    }
  }
  if (remaining.length) {
    return {
      ok: false,
      code: "extra",
      message: "منابع اضافی با الزامات خدمت سازگار نیست",
    };
  }
  return { ok: true };
}

export function eligibleResourcesForRequirements(
  resources: Resource[],
  requirements: Requirement[],
): Resource[] {
  if (!requirements.length) return resources.filter((r) => r.is_active);
  return resources.filter((resource) => {
    if (!resource.is_active) return false;
    return requirements.some((req) => {
      if (req.specific_resource_id) {
        return req.specific_resource_id === resource.id;
      }
      return req.required_resource_type === resource.resource_type;
    });
  });
}

export function requiredSelectionCount(requirements: Requirement[]): number {
  if (!requirements.length) return 1;
  return requirements.reduce((sum, req) => sum + req.quantity_required, 0);
}
