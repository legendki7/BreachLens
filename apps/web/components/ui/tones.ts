export type Tone = "neutral" | "safe" | "guard" | "breach" | "skipped" | "pending";

export type OutcomeKind =
  | "not_tested"
  | "safe_refusal"
  | "breach"
  | "blocked_input"
  | "blocked_output"
  | "pending";

export const OUTCOME_LABELS: Record<OutcomeKind, { label: string; tone: Tone }> = {
  not_tested: { label: "Not tested", tone: "skipped" },
  safe_refusal: { label: "Safe refusal", tone: "safe" },
  breach: { label: "Breach", tone: "breach" },
  blocked_input: { label: "Blocked by input guardrail", tone: "guard" },
  blocked_output: { label: "Blocked by output guardrail", tone: "guard" },
  pending: { label: "Pending", tone: "pending" },
};

export const TONE_TEXT: Record<Tone, string> = {
  neutral: "text-bone-100",
  safe: "text-safe",
  guard: "text-guard",
  breach: "text-signal-text",
  skipped: "text-bone-300",
  pending: "text-bone-400",
};

export const TONE_CHIP: Record<Tone, string> = {
  neutral: "border-ink-500 bg-ink-800 text-bone-100",
  safe: "border-safe/40 bg-safe/10 text-safe",
  guard: "border-guard/40 bg-guard/10 text-guard",
  breach: "border-signal/50 bg-signal/10 text-signal-text",
  skipped: "border-dashed border-ink-400 bg-transparent text-bone-300",
  pending: "border-dotted border-ink-500 bg-transparent text-bone-400",
};

export const TONE_DOT: Record<Tone, string> = {
  neutral: "bg-bone-200",
  safe: "bg-safe",
  guard: "bg-guard",
  breach: "bg-signal",
  skipped: "border border-dashed border-bone-300 bg-transparent",
  pending: "border border-dotted border-bone-400 bg-transparent",
};

export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
