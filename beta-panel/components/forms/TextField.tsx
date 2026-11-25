import { useId, type InputHTMLAttributes } from "react";

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
  error?: string;
};

export function TextField({ label, hint, error, id, className = "", ...props }: TextFieldProps) {
  const autoId = useId();
  const fieldId = id || props.name || autoId;
  const noteId = hint || error ? `${fieldId}-note` : undefined;
  return (
    <label className="block space-y-1 text-sm" htmlFor={fieldId}>
      {label ? <span className="ds-field-label">{label}</span> : null}
      <input
        id={fieldId}
        className={`ds-input ${className}`.trim()}
        aria-describedby={noteId}
        aria-invalid={error ? true : undefined}
        {...props}
      />
      {error ? (
        <span id={noteId} className="ds-field-error block">
          {error}
        </span>
      ) : hint ? (
        <span id={noteId} className="ds-hint block">
          {hint}
        </span>
      ) : null}
    </label>
  );
}
