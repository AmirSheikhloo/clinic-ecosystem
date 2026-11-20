"use client";

import { FormEvent, Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
      <div className="mb-8 text-center">
        <p className="text-3xl font-bold text-[var(--color-sea-deep)]">کلینیک اکوسیستم</p>
        <p className="mt-2 text-[var(--color-ink)]/70">ورود کارکنان — محیط توسعه BETA-01B</p>
      </div>
      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-2xl border border-[#d7e0ea] bg-white/90 p-6 shadow-[0_20px_50px_rgba(15,110,140,0.08)]"
      >
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">شناسه ورود</span>
          <input
            className="w-full rounded-lg border border-[#c9d5e1] bg-white px-3 py-2 outline-none focus:border-[var(--color-sea)]"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">رمز عبور</span>
          <input
            type="password"
            className="w-full rounded-lg border border-[#c9d5e1] bg-white px-3 py-2 outline-none focus:border-[var(--color-sea)]"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {(error || expiredHint) && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-[var(--color-alert)]" role="alert">
            {error || expiredHint}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-[var(--color-sea)] px-4 py-2.5 font-medium text-white transition hover:bg-[var(--color-sea-deep)] disabled:opacity-60"
        >
          {busy ? "در حال ورود…" : "ورود"}
        </button>
      </form>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<p className="text-center text-[var(--color-ink)]/60">بارگذاری…</p>}>
      <LoginForm />
    </Suspense>
  );
}
