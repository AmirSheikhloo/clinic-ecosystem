/** Re-created on every navigation: only the page content fades in (opacity, no movement). */
export default function WorkspaceTemplate({ children }: { children: React.ReactNode }) {
  return <div className="ds-page-content">{children}</div>;
}
