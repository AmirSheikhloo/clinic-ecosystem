import type { ComponentPropsWithRef, ReactNode } from "react";
import { Icon } from "./Icon";
import type { IconName } from "./icon-paths";

type Variant = "primary" | "ghost" | "subtle" | "danger" | "danger-solid";

type Props = ComponentPropsWithRef<"button"> & {
  variant?: Variant;
  size?: "sm" | "md";
  icon?: IconName;
  loading?: boolean;
  children?: ReactNode;
};

const VARIANT_CLASS: Record<Variant, string> = {
  primary: "ds-btn-primary",
  ghost: "ds-btn-ghost",
  subtle: "ds-btn-subtle",
  danger: "ds-btn-danger",
  "danger-solid": "ds-btn-danger-solid",
};

export function Button({
  variant = "primary",
  size = "md",
  icon,
  loading = false,
  className = "",
  type = "button",
  disabled,
  children,
  ...rest
}: Props) {
  const iconOnly = !children && icon;
  return (
    <button
      type={type}
      className={`ds-btn ${VARIANT_CLASS[variant]} ${size === "sm" ? "ds-btn-sm" : ""} ${
        iconOnly ? "ds-btn-icon" : ""
      } ${className}`.trim()}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <span className="ds-spinner" aria-hidden="true" /> : icon ? <Icon name={icon} size="sm" /> : null}
      {children}
    </button>
  );
}
