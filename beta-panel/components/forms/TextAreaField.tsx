import type { TextareaHTMLAttributes } from "react";

type Props = TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string };

export function TextAreaField({ label, id, className = "", ...props }: Props) {
  const fieldId = id || props.name;
  return (
    <label className="block space-y-1 text-sm" htmlFor={fieldId}>
      {label ? <span className="ds-field-label">{label}</span> : null}
      <textarea id={fieldId} className={`ds-input ${className}`.trim()} {...props} />
    </label>
  );
}
