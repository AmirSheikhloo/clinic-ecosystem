import { useId, type InputHTMLAttributes } from "react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { label: string; hint?: string };

export function CheckboxField({ label, hint, id, className = "", ...props }: Props) {
  const autoId = useId();
  const fieldId = id || props.name || autoId;
  return (
    <label className="flex items-start gap-2.5 text-sm" htmlFor={fieldId}>
      <input id={fieldId} type="checkbox" className={`ds-check mt-0.5 ${className}`.trim()} {...props} />
      <span>
        <span className="block">{label}</span>
        {hint ? <span className="ds-hint block">{hint}</span> : null}
      </span>
    </label>
  );
}
