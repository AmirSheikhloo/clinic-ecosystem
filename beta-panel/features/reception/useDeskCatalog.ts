"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/components/session/SessionProvider";
import { apiFetch, formatApiError, type ApiErrorBody } from "@/lib/client";
import type { Resource } from "@/lib/resources";
import type { RequirementsState, Service } from "./types";

/**
 * Services, resources and per-service requirements for the booking form.
 * Requirement loads are token-guarded so a stale response never overwrites a newer service.
 */
export function useDeskCatalog(onServiceChange: () => void) {
  const router = useRouter();
  const { status } = useSession();
  const [catalogReady, setCatalogReady] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [serviceId, setServiceId] = useState("");
  const [requirementsState, setRequirementsState] = useState<RequirementsState>({ status: "idle" });
  const reqToken = useRef(0);

  useEffect(() => {
    if (status !== "ready") return;
    let cancelled = false;
    async function boot() {
      try {
        const [svcRes, resRes] = await Promise.all([
          apiFetch("/api/catalog/services"),
          apiFetch("/api/catalog/resources"),
        ]);
        if (cancelled) return;
        if (svcRes.status === 401 || resRes.status === 401) {
          router.replace("/login?expired=1");
          return;
        }
        if (!svcRes.ok || !resRes.ok) {
          setCatalogError("بارگذاری فهرست خدمات/منابع ناموفق بود");
          return;
        }
        const svcData = await svcRes.json();
        const resData = await resRes.json();
        if (cancelled) return;
        setServices(svcData.items || []);
        setResources(resData.items || []);
        setCatalogReady(true);
      } catch {
        if (!cancelled) setCatalogError("ارتباط برای آماده‌سازی میز پذیرش برقرار نشد");
      }
    }
    void boot();
    return () => {
      cancelled = true;
    };
  }, [router, status]);

  useEffect(() => {
    if (!serviceId) return;
    if (requirementsState.status !== "loading") return;
    if (requirementsState.serviceId !== serviceId) return;

    const token = reqToken.current;
    const requestedServiceId = serviceId;

    async function loadRequirements() {
      try {
        const response = await apiFetch(
          `/api/catalog/resources?service_id=${encodeURIComponent(requestedServiceId)}`,
        );
        if (token !== reqToken.current) return;
        if (response.status === 401) {
          router.replace("/login?expired=1");
          return;
        }
        if (!response.ok) {
          const data = (await response.json().catch(() => ({}))) as ApiErrorBody;
          if (token !== reqToken.current) return;
          setRequirementsState({
            status: "error",
            serviceId: requestedServiceId,
            message: formatApiError(data, "خواندن الزامات منابع ناموفق بود"),
          });
          return;
        }
        const data = await response.json();
        if (token !== reqToken.current) return;
        setRequirementsState({ status: "ready", serviceId: requestedServiceId, items: data.items || [] });
      } catch {
        if (token !== reqToken.current) return;
        setRequirementsState({
          status: "error",
          serviceId: requestedServiceId,
          message: "ارتباط برای خواندن الزامات منابع برقرار نشد",
        });
      }
    }
    void loadRequirements();
  }, [serviceId, requirementsState, router]);

  function changeService(nextServiceId: string) {
    reqToken.current += 1;
    setServiceId(nextServiceId);
    onServiceChange();
    setRequirementsState(
      nextServiceId ? { status: "loading", serviceId: nextServiceId } : { status: "idle" },
    );
  }

  const durationMinutes = useMemo(
    () => services.find((s) => s.id === serviceId)?.default_duration_minutes || 30,
    [services, serviceId],
  );

  const requirementsReady =
    !!serviceId && requirementsState.status === "ready" && requirementsState.serviceId === serviceId;

  const requirements = useMemo(
    () => (requirementsReady && requirementsState.status === "ready" ? requirementsState.items : []),
    [requirementsReady, requirementsState],
  );

  return {
    sessionStatus: status,
    catalogReady,
    catalogError,
    services,
    resources,
    serviceId,
    changeService,
    requirementsState,
    requirementsReady,
    requirements,
    durationMinutes,
  };
}

export type DeskCatalog = ReturnType<typeof useDeskCatalog>;
