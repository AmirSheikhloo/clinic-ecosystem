type Props = {
  tone?: "danger" | "ok";
  children: React.ReactNode;
  role?: "alert" | "status";
  testId?: string;
};

export function Alert({ tone = "danger", children, role, testId }: Props) {
  return (
    <p
      className={tone === "danger" ? "ds-alert-danger" : "ds-alert-ok"}
      role={role ?? (tone === "danger" ? "alert" : "status")}
      data-testid={testId}
    >
      {children}
    </p>
  );
}
