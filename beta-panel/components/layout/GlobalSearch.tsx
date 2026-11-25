"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/ui/Icon";
import { apiJson, buildQuery } from "@/lib/api";
import {
  SEARCH_KIND_LABEL,
  SEARCH_MIN_LENGTH,
  isTypingTarget,
  searchHitHref,
  type SearchHit,
} from "@/lib/search-links";

const DEBOUNCE_MS = 250;

export function GlobalSearch() {
  const router = useRouter();
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [settled, setSettled] = useState<{ q: string; hits: SearchHit[]; failed: boolean } | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const term = query.trim();
  const searchable = term.length >= SEARCH_MIN_LENGTH;

  useEffect(() => {
    if (!searchable) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void apiJson<{ items: SearchHit[] }>(`/api/v1/search${buildQuery({ q: term })}`, {
        signal: controller.signal,
      }).then((result) => {
        if (controller.signal.aborted) return;
        setSettled({ q: term, hits: result.ok ? result.data.items : [], failed: !result.ok });
        setActive(0);
      });
    }, DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [term, searchable]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const mod = event.ctrlKey || event.metaKey;
      if ((event.key === "/" && !mod && !isTypingTarget(event.target)) || (mod && event.key.toLowerCase() === "k")) {
        event.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const current = searchable && settled?.q === term ? settled : null;
  const hits = current?.hits ?? [];

  function go(hit: SearchHit) {
    setOpen(false);
    setQuery("");
    router.push(searchHitHref(hit));
  }

  function onInputKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    } else if (event.key === "ArrowDown" && hits.length) {
      event.preventDefault();
      setActive((value) => (value + 1) % hits.length);
    } else if (event.key === "ArrowUp" && hits.length) {
      event.preventDefault();
      setActive((value) => (value - 1 + hits.length) % hits.length);
    } else if (event.key === "Enter" && hits[active]) {
      event.preventDefault();
      go(hits[active]);
    }
  }

  return (
    <div className="relative w-full" data-testid="global-search">
      <Icon name="search" size="sm" className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-[var(--ds-text-muted)]" />
      <input
        ref={inputRef}
        type="search"
        className="ds-input !ps-9"
        placeholder="جستجوی بیمار، خدمت، منبع… ( / )"
        aria-label="جستجوی سراسری"
        role="combobox"
        aria-expanded={open && searchable}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        value={query}
        data-testid="global-search-input"
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        onKeyDown={onInputKeyDown}
      />
      {open && searchable ? (
        <ul
          id={listId}
          role="listbox"
          className="ds-card absolute inset-x-0 top-full z-[var(--ds-z-popover)] mt-1 max-h-80 overflow-auto p-1 text-sm shadow-[var(--ds-shadow)] animate-fade-in"
          data-testid="global-search-results"
        >
          {!current ? <li className="px-3 py-2 text-[var(--ds-text-muted)]">در حال جستجو…</li> : null}
          {current?.failed ? <li className="px-3 py-2 text-[var(--ds-danger)]">جستجو ناموفق بود</li> : null}
          {current && !current.failed && hits.length === 0 ? (
            <li className="px-3 py-2 text-[var(--ds-text-muted)]">نتیجه‌ای یافت نشد</li>
          ) : null}
          {hits.map((hit, index) => (
            <li
              key={`${hit.kind}-${hit.id}`}
              role="option"
              aria-selected={index === active}
              data-testid="global-search-hit"
              className={`flex cursor-pointer items-center justify-between gap-2 rounded-md px-3 py-2 ${
                index === active ? "bg-[var(--ds-primary-soft)]" : ""
              }`}
              onMouseDown={(event) => {
                event.preventDefault();
                go(hit);
              }}
              onMouseEnter={() => setActive(index)}
            >
              <span>
                {hit.title}
                {hit.subtitle ? (
                  <span className="ms-2 text-xs text-[var(--ds-text-muted)]">{hit.subtitle}</span>
                ) : null}
              </span>
              <span className="ds-badge">{SEARCH_KIND_LABEL[hit.kind]}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
