import type { HTMLAttributes } from "react";

export function Card({
  className = "",
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={`ds-card p-5 ${className}`.trim()} {...rest} />;
}
