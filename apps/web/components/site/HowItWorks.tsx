import { SectionHeading } from "./SectionHeading";

const PIPELINE = ["Attack", "Input check", "Target", "Output check", "Evaluation", "Evidence"];

const STEPS: Array<{ title: string; body: string }> = [
  { title: "Configure", body: "Choose a scenario, a target model, a guardrail policy, and a turn limit." },
  { title: "Attack", body: "An attacker model writes one test prompt for the scenario, using a selected technique." },
  { title: "Input check", body: "Input guardrails inspect the prompt. If it is blocked, the target is never called." },
  { title: "Target", body: "If the prompt is allowed, the target model responds." },
  { title: "Output check", body: "Output guardrails inspect the raw response before it reaches the user." },
  {
    title: "Evaluate",
    body: "Deterministic evidence checks and an LLM judge assess the raw model behavior against a versioned rubric.",
  },
  {
    title: "Record",
    body: "The system outcome is derived separately from the guardrail decisions, and the turn's evidence is stored.",
  },
  { title: "Adapt", body: "Earlier results inform the attacker's next attempt." },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="how-title" className="border-b border-ink-700 py-20 sm:py-28">
      <div className="page-x">
        <SectionHeading index="02" eyebrow="How it works" id="how-title" title="One turn, six stages, two verdicts.">
          <p>
            An assessment is a series of turns against one target. Every turn follows the same path, and every stage
            leaves evidence behind.
          </p>
        </SectionHeading>

        <div className="mt-14 lg:ml-[calc(25%+0.625rem)]">
          <ol
            aria-label="Stages of one turn"
            className="grid grid-cols-2 gap-px overflow-hidden rounded-[4px] border border-ink-600 bg-ink-600 sm:grid-cols-3 lg:grid-cols-6"
          >
            {PIPELINE.map((stage, index) => (
              <li key={stage} className="relative bg-ink-900 px-4 py-4">
                <span className="font-mono text-[0.75rem] text-bone-300">{String(index + 1).padStart(2, "0")}</span>
                <span className="mt-2 block text-[0.9375rem] font-semibold text-bone-50">{stage}</span>
                {index === 0 ? <span aria-hidden="true" className="absolute inset-x-0 top-0 h-0.5 bg-signal" /> : null}
              </li>
            ))}
          </ol>
          <p className="mt-3 flex items-center gap-2 text-[0.9375rem] text-bone-300">
            <span aria-hidden="true" className="font-mono text-bone-200">↺</span>
            The next turn starts at Attack, informed by what earlier turns revealed.
          </p>
        </div>

        <ol className="mt-16 grid gap-x-10 gap-y-9 sm:grid-cols-2 lg:ml-[calc(25%+0.625rem)]">
          {STEPS.map((step, index) => (
            <li key={step.title} className="grid grid-cols-[2.5rem_1fr] gap-x-3 border-t border-ink-700 pt-5">
              <span className="font-mono text-[0.875rem] text-signal-text">{String(index + 1).padStart(2, "0")}</span>
              <div>
                <h3 className="text-lg font-semibold text-bone-50">{step.title}</h3>
                <p className="mt-1.5 text-base leading-relaxed text-bone-200">{step.body}</p>
              </div>
            </li>
          ))}
        </ol>

        <aside className="mt-14 max-w-3xl border-l-2 border-guard/70 py-1 pl-5 lg:ml-[calc(25%+0.625rem)]">
          <p className="text-base leading-relaxed text-bone-100">
            <span className="font-semibold text-bone-50">Multi-turn today.</span> The attacker adapts between turns.
            The target currently receives each prompt as an independent message, without conversation history.
          </p>
        </aside>
      </div>
    </section>
  );
}
