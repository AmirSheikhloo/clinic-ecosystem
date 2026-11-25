import { useId, type TextareaHTMLAttributes } from "react";

type Props = TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string; hint?: string };

export function TextAreaField({ label, hint, id, className = "", ...props }: Props) {
  const autoId = useId();
  const fieldId = id || props.name || autoId;
  return (
    <label className="block space-y-1 text-sm" htmlFor={fieldId}>
      {label ? <span className="ds-field-label">{label}</span> : null}
      <textarea id={fieldId} className={`ds-input ${className}`.trim()} {...props} />
      {hint ? <span className="ds-hint block">{hint}</span> : null}
    </label>
  );
}
