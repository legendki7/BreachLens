import type { ReactNode } from "react";

export function SectionHeading({
  index,
  eyebrow,
  title,
  id,
  children,
}: {
  index: string;
  eyebrow: string;
  title: ReactNode;
  id: string;
  children?: ReactNode;
}) {
  return (
    <div className="grid gap-6 lg:grid-cols-12 lg:gap-10">
      <p className="eyebrow lg:col-span-3 lg:pt-3">
        <span className="text-signal-text">{index}</span>
        <span aria-hidden="true" className="mx-2 text-ink-400">
          /
        </span>
        {eyebrow}
      </p>
      <div className="lg:col-span-9">
        <h2
          id={id}
          className="max-w-3xl text-balance text-[2rem] font-semibold leading-[1.08] tracking-[-0.02em] text-bone-50 sm:text-[2.75rem]"
        >
          {title}
        </h2>
        {children ? (
          <div className="mt-5 max-w-2xl text-lg leading-relaxed text-bone-200">{children}</div>
        ) : null}
      </div>
    </div>
  );
}
