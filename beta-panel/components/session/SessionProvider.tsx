"use client";

import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { SESSION_EXPIRED_EVENT } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api-query";

/** Authorization is re-read periodically and on return to the tab; it is never trusted indefinitely. */
const REVALIDATE_INTERVAL_MS = 5 * 60_000;
const REVALIDATE_AFTER_HIDDEN_MS = 60_000;

export type Me = {
  account_id: string;
  tenant_id: string;
  login_identifier: string;
  is_active: boolean;
  first_name: string;
  last_name: string;
  permissions: string[];
  governance_roles: string[];
};

type SessionValue = {
  status: "loading" | "ready" | "error";
  me: Me | null;
  permissions: ReadonlySet<string>;
  can: (code: string) => boolean;
  canAny: (codes: readonly string[]) => boolean;
};

const EMPTY: ReadonlySet<string> = new Set();
const SessionContext = createContext<SessionValue>({
  status: "loading",
  me: null,
  permissions: EMPTY,
  can: () => false,
  canAny: () => false,
});

export function SessionProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const query = useApiQuery<Me>("/api/auth/me", "نشست معتبر نیست");

  useEffect(() => {
    const onExpired = () => router.replace("/login?expired=1");
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, [router]);

  const reload = query.reload;
  useEffect(() => {
    let lastCheck = Date.now();
    const revalidate = () => {
      lastCheck = Date.now();
      reload();
    };
    const timer = window.setInterval(revalidate, REVALIDATE_INTERVAL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible" && Date.now() - lastCheck > REVALIDATE_AFTER_HIDDEN_MS) revalidate();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [reload]);

  const value = useMemo<SessionValue>(() => {
    const permissions = new Set(query.data?.permissions ?? []);
    return {
      status: query.loading ? "loading" : query.data ? "ready" : "error",
      me: query.data,
      permissions,
      can: (code) => permissions.has(code),
      canAny: (codes) => codes.some((code) => permissions.has(code)),
    };
  }, [query.data, query.loading]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  return useContext(SessionContext);
}
