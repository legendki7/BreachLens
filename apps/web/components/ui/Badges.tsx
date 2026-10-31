import { OUTCOME_LABELS, TONE_CHIP, TONE_DOT, cx, type OutcomeKind, type Tone } from "./tones";

export function StatusChip({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span
      className={cx(
        "inline-flex max-w-full items-center gap-1.5 rounded-[3px] border px-2 py-0.5 text-left font-mono text-[0.75rem] font-medium uppercase tracking-[0.06em]",
        TONE_CHIP[tone],
      )}
    >
      <span aria-hidden="true" className={cx("h-1.5 w-1.5 shrink-0 rounded-full", TONE_DOT[tone])} />
      {children}
    </span>
  );
}

export function Verdict({
  heading,
  outcome,
  size = "md",
}: {
  heading: string;
  outcome: OutcomeKind;
  size?: "md" | "lg";
}) {
  const { label, tone } = OUTCOME_LABELS[outcome];
  return (
    <div className="min-w-0">
      <p className="font-mono text-[0.75rem] uppercase tracking-[0.12em] text-bone-300">{heading}</p>
      <p
        className={cx(
          "mt-2 flex items-start gap-2.5 font-semibold leading-tight",
          size === "lg" ? "text-2xl sm:text-[1.75rem]" : "text-lg",
          tone === "breach" && "text-signal-text",
          tone === "guard" && "text-guard",
          tone === "safe" && "text-safe",
          (tone === "skipped" || tone === "pending") && "text-bone-300",
        )}
      >
        <span
          aria-hidden="true"
          className={cx(
            "mt-[0.45em] h-2.5 w-2.5 shrink-0 rounded-[2px]",
            TONE_DOT[tone],
          )}
        />
        <span>{label}</span>
      </p>
    </div>
  );
}
