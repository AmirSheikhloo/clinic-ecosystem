import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "ghost";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...rest
}: Props) {
  const variantClass = variant === "primary" ? "ds-btn-primary" : "ds-btn-ghost";
  return (
    <button
      type={type}
      className={`ds-btn ${variantClass} ${className}`.trim()}
      {...rest}
    />
  );
}
