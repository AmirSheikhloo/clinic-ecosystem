import type { InputHTMLAttributes } from "react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { label: string; hint?: string };

export function CheckboxField({ label, hint, id, className = "", ...props }: Props) {
  const fieldId = id || props.name;
  return (
    <label className="flex items-start gap-2 text-sm" htmlFor={fieldId}>
      <input id={fieldId} type="checkbox" className={`mt-1 h-4 w-4 ${className}`.trim()} {...props} />
      <span>
        <span className="block">{label}</span>
        {hint ? <span className="block text-xs text-[var(--ds-text-muted)]">{hint}</span> : null}
      </span>
    </label>
  );
}
