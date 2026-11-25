import type { SelectHTMLAttributes, ReactNode } from "react";

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  children: ReactNode;
};

export function SelectField({
  label,
  id,
  className = "",
  children,
  ...props
}: SelectFieldProps) {
  const fieldId = id || props.name;
  return (
    <label className="block space-y-1 text-sm" htmlFor={fieldId}>
      {label ? <span className="ds-field-label">{label}</span> : null}
      <select id={fieldId} className={`ds-input ${className}`.trim()} {...props}>
        {children}
      </select>
    </label>
  );
}
