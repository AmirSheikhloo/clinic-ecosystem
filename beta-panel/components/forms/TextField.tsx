import type { InputHTMLAttributes } from "react";

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
};

export function TextField({ label, id, className = "", ...props }: TextFieldProps) {
  const fieldId = id || props.name;
  return (
    <label className="block space-y-1 text-sm" htmlFor={fieldId}>
      {label ? <span className="ds-field-label">{label}</span> : null}
      <input id={fieldId} className={`ds-input ${className}`.trim()} {...props} />
    </label>
  );
}
