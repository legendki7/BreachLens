import Image from "next/image";

import { NAV_LINKS } from "./navigation";

export function SiteFooter() {
  return (
    <footer className="border-t border-ink-700 bg-ink-900">
      <div className="page-x grid gap-10 py-14 md:grid-cols-12">
        <div className="md:col-span-6">
          <Image src="/brand/breachlens-logo.png" alt="BreachLens" width={1094} height={246} sizes="160px" className="h-7 w-auto" />
          <p className="mt-5 max-w-md text-base leading-relaxed text-bone-200">
            BreachLens is an AI security assessment project. Prototype stage: the backend workflow is implemented and
            end-to-end validation is in progress.
          </p>
        </div>
        <nav aria-label="Footer" className="md:col-span-3 md:col-start-8">
          <ul className="space-y-3">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <a href={link.href} className="text-[0.9375rem] text-bone-200 hover:text-bone-50">
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <p className="text-[0.875rem] leading-relaxed text-bone-300 md:col-span-12">
          Third-party models and open-source frameworks used in testing are not developed by BreachLens. © 2026 BreachLens.
        </p>
      </div>
    </footer>
  );
}
