import { CheckboxField } from "@/components/forms/CheckboxField";
import { CATEGORY_LABEL, groupByCategory, toggleInSet, type PermissionDef } from "./types";

type Props = {
  catalog: PermissionDef[];
  selected: string[];
  onChange: (next: string[]) => void;
  /** Codes the editor may not grant (anti-escalation is enforced server-side too). */
  disabledCodes?: ReadonlySet<string>;
};

export function PermissionPicker({ catalog, selected, onChange, disabledCodes }: Props) {
  return (
    <div className="space-y-4" data-testid="permission-picker">
      {groupByCategory(catalog).map(([category, items]) => (
        <fieldset key={category} className="space-y-2">
          <legend className="mb-1 text-sm font-semibold text-[var(--ds-primary-strong)]">
            {CATEGORY_LABEL[category] ?? category}
          </legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {items.map((item) => (
              <CheckboxField
                key={item.code}
                id={`perm-${item.code}`}
                label={item.label_fa}
                hint={item.description}
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
