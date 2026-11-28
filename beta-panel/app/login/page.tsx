"use client";

import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Alert } from "@/components/feedback/Alert";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { apiFetch, ensureCsrf, formatApiError, type ApiErrorBody } from "@/lib/client";
import { clearQueryCache } from "@/lib/query-cache";

type DemoRole = { alias: string; label_fa: string };
type DemoCatalog = { enabled: boolean; password_hint?: string | null; roles: DemoRole[] };

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [demo, setDemo] = useState<DemoCatalog | null>(null);
  const expiredHint = useMemo(
    () => (searchParams.get("expired") === "1" ? "نشست منقضی شده — دوباره وارد شوید" : null),
    [searchParams],
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const response = await apiFetch("/api/auth/demo-aliases");
        if (!response.ok) return;
        const data = (await response.json()) as DemoCatalog;
        if (!cancelled) setDemo(data);
      } catch {
        /* fail closed: normal login only */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function signIn(identifier: string, pwd: string) {
    setError(null);
    setBusy(true);
    try {
      await ensureCsrf();
      // Clear prior principal/session before establishing a new role (demo switch).
      try {
        await apiFetch("/api/auth/logout", { method: "POST", csrf: true });
      } catch {
        /* best-effort — login still replaces cookies */
      }
      clearQueryCache();
      await ensureCsrf();
      const response = await apiFetch("/api/auth/login", {
        method: "POST",
        csrf: true,
        body: JSON.stringify({
          login_identifier: identifier,
          password: pwd,
        }),
      });
      const data = (await response.json().catch(() => ({}))) as ApiErrorBody;
      if (!response.ok) {
        setError(formatApiError(data, "ورود ناموفق بود"));
        return;
      }
      clearQueryCache();
      router.replace("/dashboard");
    } catch {
      setError("ارتباط با سرویس برقرار نشد");
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    await signIn(login, password);
  }

  async function onDemoRole(alias: string) {
    const pwd = demo?.password_hint || "Clinic123!";
    setLogin(alias);
    setPassword(pwd);
    await signIn(alias, pwd);
  }

  return (
    <main className="mx-auto flex min-h-[80vh] max-w-lg flex-col justify-center animate-rise">
      <div className="mb-8 flex flex-col items-center gap-3 text-center">
        <span className="ds-brand-mark !h-12 !w-12 !bg-[var(--ds-primary)] text-[var(--ds-on-primary)]" aria-hidden="true">
          <Icon name="stethoscope" size="lg" />
        </span>
        <h1 className="text-2xl font-bold text-[var(--ds-heading)]">کلینیک اکوسیستم</h1>
        <p className="text-sm text-[var(--ds-text-muted)]">ورود کارکنان به پنل عملیات</p>
      </div>

      {demo?.enabled && demo.roles.length > 0 ? (
        <section className="ds-card mb-4 space-y-3 p-5" aria-label="ورود سریع نقش‌های آزمایشی" data-testid="demo-role-selector">
          <div>
            <h2 className="text-sm font-semibold text-[var(--ds-heading)]">ورود سریع (محیط مصنوعی)</h2>
            <p className="text-xs text-[var(--ds-text-muted)]">
              رمز مشترک تمام نقش‌ها: <span className="ltr-isolate font-mono" dir="ltr">{demo.password_hint}</span>
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {demo.roles.map((role) => (
              <button
                key={role.alias}
                type="button"
                className="ds-btn ds-btn-secondary min-h-10 px-2 text-xs"
                disabled={busy}
                data-testid={`demo-role-${role.alias}`}
                onClick={() => void onDemoRole(role.alias)}
              >
                {role.label_fa}
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <form onSubmit={onSubmit} className="ds-card space-y-4 p-6" aria-label="ورود به پنل">
        <TextField
          label="شناسهٔ ورود"
          data-testid="login-identifier"
          value={login}
          onChange={(e) => setLogin(e.target.value)}
          autoComplete="username"
          dir="ltr"
          className="text-right"
          required
        />
        <TextField
          label="رمز عبور"
          type="password"
          data-testid="login-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          dir="ltr"
          className="text-right"
          required
        />
        {error || expiredHint ? <Alert tone={error ? "danger" : "warn"} testId="login-message">{error || expiredHint}</Alert> : null}
        <Button type="submit" loading={busy} data-testid="login-submit" className="w-full">
          {busy ? "در حال ورود…" : "ورود"}
        </Button>
      </form>
      <p className="mt-4 text-center text-xs text-[var(--ds-text-muted)]">نسخهٔ آزمایشی: فقط با داده‌های مصنوعی استفاده شود.</p>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
