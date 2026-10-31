import { StatusChip } from "../ui/Badges";
import type { Tone } from "../ui/tones";
import { SectionHeading } from "./SectionHeading";

const MILESTONES: Array<{ state: string; tone: Tone; title: string; body: string }> = [
  {
    state: "Implemented",
    tone: "safe",
    title: "Backend assessment workflow",
    body: "Attacker, input and output guardrails, target call, deterministic checks, LLM judge, outcome composition, and per-turn evidence storage are implemented in source.",
  },
  {
    state: "In progress",
    tone: "guard",
    title: "End-to-end validation",
    body: "Running complete assessments against real models with a persistent database. No completed live run has been published yet.",
  },
  {
    state: "Planned",
    tone: "pending",
    title: "Assessment interface and more providers",
    body: "An interactive interface for configuring and reviewing assessments, and model providers beyond Hugging Face, including OpenAI and Anthropic.",
  },
];

const BOUNDARIES = [
  "Hugging Face is the only model provider implemented today.",
  "Guardrails are a small set of pattern-based checks, not comprehensive protection.",
  "The attacker adapts between turns. The target sees each prompt as an independent message.",
  "Turn-ready scenarios today cover jailbreak, direct and indirect prompt injection, and hidden-context exposure.",
  "The demo on this page is simulated. It is not the assessment application.",
];

export function ProjectStatus() {
  return (
    <section id="status" aria-labelledby="status-title" className="py-20 sm:py-28">
      <div className="page-x">
        <SectionHeading index="06" eyebrow="Project status" id="status-title" title="Where BreachLens stands today." />

        <ol className="mt-14 grid gap-px overflow-hidden rounded-[4px] border border-ink-600 bg-ink-600 md:grid-cols-3 lg:ml-[calc(25%+0.625rem)]">
          {MILESTONES.map((milestone) => (
            <li key={milestone.title} className="bg-ink-900 px-5 py-6">
              <StatusChip tone={milestone.tone}>{milestone.state}</StatusChip>
              <h3 className="mt-4 text-lg font-semibold leading-snug text-bone-50">{milestone.title}</h3>
              <p className="mt-2 text-[0.9375rem] leading-relaxed text-bone-200">{milestone.body}</p>
            </li>
          ))}
        </ol>

        <div className="mt-12 lg:ml-[calc(25%+0.625rem)]">
          <h3 className="text-lg font-semibold text-bone-50">Current boundaries</h3>
          <ul className="mt-4 grid gap-x-10 gap-y-3 md:grid-cols-2">
            {BOUNDARIES.map((item) => (
              <li key={item} className="flex gap-3 text-base leading-relaxed text-bone-200">
                <span aria-hidden="true" className="mt-[0.7em] h-1 w-3 shrink-0 bg-ink-400" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
