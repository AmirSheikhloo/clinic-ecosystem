import { ICON_PATHS, type IconName } from "./icon-paths";

type Props = { name: IconName; size?: "sm" | "md" | "lg"; className?: string };

const SIZE_CLASS = { sm: "ds-icon ds-icon-sm", md: "ds-icon", lg: "ds-icon ds-icon-lg" } as const;

/** Decorative icon; pair with visible text or an aria-label on the control. */
export function Icon({ name, size = "md", className = "" }: Props) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={`${SIZE_CLASS[size]} ${className}`.trim()}
    >
      {ICON_PATHS[name].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}
