"use client";

import { FormEvent, Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Alert } from "@/components/feedback/Alert";
import { TextField } from "@/components/forms/TextField";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { apiFetch, ensureCsrf, formatApiError, type ApiErrorBody } from "@/lib/client";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const expiredHint = useMemo(
    () => (searchParams.get("expired") === "1" ? "نشست منقضی شده — دوباره وارد شوید" : null),
    [searchParams],
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await ensureCsrf();
      const response = await apiFetch("/api/auth/login", {
        method: "POST",
        csrf: true,
        body: JSON.stringify({
          login_identifier: login,
          password,
        }),
      });
      const data = (await response.json().catch(() => ({}))) as ApiErrorBody;
      if (!response.ok) {
        setError(formatApiError(data, "ورود ناموفق بود"));
        return;
      }
      router.replace("/desk");
    } catch {
      setError("ارتباط با سرویس برقرار نشد");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-[80vh] max-w-md flex-col justify-center animate-rise">
      <div className="mb-8 flex flex-col items-center gap-3 text-center">
        <span className="ds-brand-mark !h-12 !w-12 !bg-[var(--ds-primary)] text-[var(--ds-on-primary)]" aria-hidden="true">
          <Icon name="stethoscope" size="lg" />
        </span>
        <h1 className="text-2xl font-bold text-[var(--ds-heading)]">کلینیک اکوسیستم</h1>
        <p className="text-sm text-[var(--ds-text-muted)]">ورود کارکنان به پنل عملیات</p>
      </div>
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
