import { useId, type SelectHTMLAttributes, type ReactNode } from "react";

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  hint?: string;
  children: ReactNode;
};

export function SelectField({ label, hint, id, className = "", children, ...props }: SelectFieldProps) {
  const autoId = useId();
  const fieldId = id || props.name || autoId;
  const noteId = hint ? `${fieldId}-note` : undefined;
  return (
    <label className="block space-y-1 text-sm" htmlFor={fieldId}>
      {label ? <span className="ds-field-label">{label}</span> : null}
      <select id={fieldId} className={`ds-input ${className}`.trim()} aria-describedby={noteId} {...props}>
        {children}
      </select>
      {hint ? (
        <span id={noteId} className="ds-hint block">
          {hint}
        </span>
      ) : null}
    </label>
  );
}
