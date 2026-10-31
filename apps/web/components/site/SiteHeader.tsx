"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import { NAV_LINKS } from "./navigation";

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        toggleRef.current?.focus();
      }
    };
    const onResize = () => {
      if (window.matchMedia("(min-width: 768px)").matches) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  return (
    <header className="sticky top-0 z-40 border-b border-ink-700 bg-ink-950/95 backdrop-blur-sm">
      <div className="page-x flex h-16 items-center justify-between gap-6">
        <a href="#top" className="flex shrink-0 items-center" aria-label="BreachLens, back to top">
          <Image
            src="/brand/breachlens-logo.png"
            alt="BreachLens"
            width={1094}
            height={246}
            priority
            sizes="160px"
            className="h-7 w-auto sm:h-8"
          />
        </a>

        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center gap-7">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="text-[0.9375rem] font-medium text-bone-200 transition-colors hover:text-bone-50"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="flex items-center gap-2">
          <a href="#demo" className="btn-primary hidden min-h-10 px-4 text-[0.875rem] sm:inline-flex">
            Explore the demo
          </a>
          <button
            ref={toggleRef}
            type="button"
            className="inline-flex h-11 w-11 items-center justify-center rounded-[3px] border border-ink-500 text-bone-50 md:hidden"
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((value) => !value)}
          >
            <svg aria-hidden="true" viewBox="0 0 20 20" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6">
              {open ? (
                <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
              ) : (
                <path d="M3 6h14M3 10h14M3 14h14" strokeLinecap="round" />
              )}
            </svg>
          </button>
        </div>
      </div>

      <div id="mobile-menu" hidden={!open} className="border-t border-ink-700 bg-ink-950 md:hidden">
        <nav aria-label="Mobile" className="page-x py-3">
          <ul>
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  onClick={() => setOpen(false)}
                  className="flex min-h-12 items-center border-b border-ink-800 text-base font-medium text-bone-100"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
          <a href="#demo" onClick={() => setOpen(false)} className="btn-primary mt-4 w-full">
            Explore the demo
          </a>
        </nav>
      </div>
    </header>
  );
}
