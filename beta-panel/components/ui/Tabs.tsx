"use client";

import { useRef, type KeyboardEvent } from "react";

export type TabDef = { id: string; label: string };

type Props = { tabs: TabDef[]; active: string; onChange: (id: string) => void; label: string };

export function Tabs({ tabs, active, onChange, label }: Props) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  function onKeyDown(event: KeyboardEvent, index: number) {
    const dir = event.key === "ArrowLeft" ? 1 : event.key === "ArrowRight" ? -1 : 0;
    if (!dir) return;
    event.preventDefault();
    const next = tabs[(index + dir + tabs.length) % tabs.length];
    onChange(next.id);
    refs.current[next.id]?.focus();
  }

  return (
    <div role="tablist" aria-label={label} className="flex flex-wrap gap-1 border-b border-[var(--ds-border)]">
      {tabs.map((tab, index) => (
        <button
          key={tab.id}
          ref={(node) => {
            refs.current[tab.id] = node;
          }}
          type="button"
          role="tab"
          id={`tab-${tab.id}`}
          aria-selected={active === tab.id}
          aria-controls={`panel-${tab.id}`}
          tabIndex={active === tab.id ? 0 : -1}
          className="ds-tab"
          data-testid={`tab-${tab.id}`}
          onClick={() => onChange(tab.id)}
          onKeyDown={(event) => onKeyDown(event, index)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
