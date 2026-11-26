import { useId, type InputHTMLAttributes, type Ref } from "react";
import { Icon } from "@/components/ui/Icon";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "onChange" | "value" | "type"> & {
  label?: string;
  value: string;
  onValueChange: (value: string) => void;
  /** A request for the current term is running; shows a spinner in the clear-button slot. */
  busy?: boolean;
  inputRef?: Ref<HTMLInputElement>;
};

/** Search input with a fixed-size leading icon and trailing clear/busy slot, so the box never reflows. */
export function SearchField({ label, value, onValueChange, busy = false, inputRef, id, className = "", ...rest }: Props) {
  const autoId = useId();
  const fieldId = id || autoId;
  return (
    <label className="block space-y-1 text-sm" htmlFor={fieldId}>
      {label ? <span className="ds-field-label">{label}</span> : null}
      <span className="ds-search">
        <Icon name="search" size="sm" className="ds-search-icon" />
        <input
          id={fieldId}
          ref={inputRef}
          type="search"
          className={`ds-input ds-search-input ${className}`.trim()}
          value={value}
          onChange={(event) => onValueChange(event.target.value)}
          autoComplete="off"
          {...rest}
        />
        <span className="ds-search-trailing" aria-hidden={!busy}>
          {busy ? <span className="ds-spinner" /> : null}
        </span>
      </span>
    </label>
  );
}
