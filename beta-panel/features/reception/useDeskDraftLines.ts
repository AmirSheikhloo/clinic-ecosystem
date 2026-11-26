"use client";

import { useState } from "react";
import { tehranNowLocalInput } from "@/lib/tehran";
import type { DraftServiceLine, Service } from "./types";

type BuildArgs = {
  serviceId: string;
  services: Service[];
  resourceIds: string[];
  resourceNames: string[];
  localStart: string;
  durationMinutes: number;
  selectionOk: boolean;
};

/** Queued multi-service lines for one reception group (independent appointment IDs on submit). */
export function useDeskDraftLines() {
  const [draftLines, setDraftLines] = useState<DraftServiceLine[]>([]);

  function buildLine(args: BuildArgs, keyPrefix: string): DraftServiceLine | null {
    if (!args.serviceId || !args.localStart || !args.selectionOk) return null;
    const service = args.services.find((item) => item.id === args.serviceId);
    if (!service) return null;
    return {
      key: `${keyPrefix}-${args.serviceId}-${args.localStart}-${args.resourceIds.join(",")}`,
      serviceId: args.serviceId,
      serviceName: service.service_name,
      resourceIds: [...args.resourceIds],
      resourceNames: [...args.resourceNames],
      localStart: args.localStart,
      durationMinutes: args.durationMinutes,
      priceIrr: service.default_price_irr ?? 0,
    };
  }

  function addDraftLine(args: BuildArgs): boolean {
    const line = buildLine(args, "line");
    if (!line) return false;
    setDraftLines((prev) => [...prev, { ...line, key: `${line.key}-${prev.length}-${Date.now()}` }]);
    return true;
  }

  function removeDraftLine(key: string) {
    setDraftLines((prev) => prev.filter((line) => line.key !== key));
  }

  function clearDraftLines() {
    setDraftLines([]);
  }

  function liveDraftLine(args: BuildArgs): DraftServiceLine | null {
    return buildLine(args, "draft");
  }

  function setWalkInNow(setLocalStart: (value: string) => void) {
    setLocalStart(tehranNowLocalInput());
  }

  return {
    draftLines,
    addDraftLine,
    removeDraftLine,
    clearDraftLines,
    liveDraftLine,
    setWalkInNow,
    canSubmitGroup: draftLines.length > 0,
  };
}

export type DeskDraftLines = ReturnType<typeof useDeskDraftLines>;
