import { CheckboxField } from "@/components/forms/CheckboxField";
import { Button } from "@/components/ui/Button";
import { permissionHint } from "./permission-hints";
import { CATEGORY_LABEL, groupByCategory, toggleInSet, type PermissionDef } from "./types";

type Props = {
  catalog: PermissionDef[];
  selected: string[];
  onChange: (next: string[]) => void;
  /** Codes the editor may not grant (anti-escalation is enforced server-side too). */
  disabledCodes?: ReadonlySet<string>;
};

function addAll(selected: string[], items: PermissionDef[], disabled?: ReadonlySet<string>): string[] {
  const next = new Set(selected);
  for (const item of items) if (!disabled?.has(item.code)) next.add(item.code);
  return Array.from(next);
}

function removeAll(selected: string[], items: PermissionDef[]): string[] {
  const drop = new Set(items.map((item) => item.code));
  return selected.filter((code) => !drop.has(code));
}

export function PermissionPicker({ catalog, selected, onChange, disabledCodes }: Props) {
  return (
    <div className="space-y-4" data-testid="permission-picker">
      {groupByCategory(catalog).map(([category, items]) => (
        <fieldset key={category} className="space-y-2">
          <legend className="mb-1 flex w-full items-center justify-between gap-2 text-sm font-semibold text-[var(--ds-heading)]">
            <span>
              {CATEGORY_LABEL[category] ?? category}
              <span className="ms-2 text-xs font-normal text-[var(--ds-text-muted)] tabular-nums">
                {items.filter((item) => selected.includes(item.code)).length} از {items.length}
              </span>
            </span>
            <span className="flex gap-1">
              <Button variant="subtle" size="sm" onClick={() => onChange(addAll(selected, items, disabledCodes))} data-testid={`perm-all-${category}`}>
                انتخاب همه
              </Button>
              <Button variant="subtle" size="sm" onClick={() => onChange(removeAll(selected, items))} data-testid={`perm-none-${category}`}>
                پاک‌کردن
              </Button>
            </span>
          </legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {items.map((item) => (
              <CheckboxField
                key={item.code}
                id={`perm-${item.code}`}
                label={item.label_fa}
                hint={permissionHint(item.code)}
                checked={selected.includes(item.code)}
                disabled={disabledCodes?.has(item.code) && !selected.includes(item.code)}
                onChange={(e) => onChange(toggleInSet(selected, item.code, e.target.checked))}
                data-testid={`perm-${item.code}`}
              />
            ))}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
