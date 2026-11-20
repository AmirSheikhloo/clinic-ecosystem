"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/client";

const NAV = [
  { href: "/desk", label: "میز پذیرش" },
  { href: "/appointments", label: "نوبت‌های روز" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const hideNav = pathname === "/login" || pathname === "/";

  async function logout() {
    await apiFetch("/api/auth/logout", { method: "POST", csrf: true });
    router.replace("/login");
  }

  return (
    <div className="min-h-screen">
      {!hideNav && (
        <header className="border-b border-[#d7e0ea]/80 bg-white/70 backdrop-blur-md">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
            <div className="flex items-center gap-6">
              <Link href="/desk" className="text-lg font-bold tracking-tight text-[var(--color-sea-deep)]">
                کلینیک اکوسیستم
              </Link>
              <nav className="flex gap-3 text-sm">
                {NAV.map((item) => {
                  const active = pathname.startsWith(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={
                        active
                          ? "rounded-md bg-[var(--color-sea)] px-3 py-1.5 text-white"
                          : "rounded-md px-3 py-1.5 text-[var(--color-ink)]/80 hover:bg-[var(--color-mist)]"
                      }
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>
            <button
              type="button"
              onClick={logout}
              className="rounded-md border border-[#c9d5e1] bg-white px-3 py-1.5 text-sm hover:bg-[var(--color-mist)]"
            >
              خروج
            </button>
          </div>
        </header>
      )}
      <div className="mx-auto max-w-6xl px-4 py-6">{children}</div>
    </div>
  );
}
