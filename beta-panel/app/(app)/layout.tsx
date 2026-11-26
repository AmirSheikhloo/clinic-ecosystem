import { AppShell } from "@/components/layout/AppShell";

/** Authenticated workspaces share one persistent shell; it is not remounted between routes. */
export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
