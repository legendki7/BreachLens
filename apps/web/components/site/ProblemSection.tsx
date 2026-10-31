import { StatusChip, Verdict } from "../ui/Badges";
import type { OutcomeKind, Tone } from "../ui/tones";
import { SectionHeading } from "./SectionHeading";

interface Run {
  name: string;
  stages: Array<{ label: string; status: string; tone: Tone }>;
  story: string;
  model: OutcomeKind;
  fix: string;
}

const RUNS: Run[] = [
  {
    name: "Run 1",
    stages: [
      { label: "Input check", status: "Blocked", tone: "guard" },
      { label: "Target", status: "Not called", tone: "skipped" },
      { label: "Output check", status: "Skipped", tone: "skipped" },
    ],
    story: "The prompt never reached the model. Its behavior is unknown.",
    model: "not_tested",
    fix: "Model resilience is still unmeasured. A separate test is needed to learn how the model behaves.",
  },
  {
    name: "Run 2",
    stages: [
      { label: "Input check", status: "Allowed", tone: "neutral" },
      { label: "Target", status: "Leaked value", tone: "breach" },
      { label: "Output check", status: "Blocked", tone: "guard" },
    ],
    story: "The model disclosed the protected value. A filter caught it on the way out.",
    model: "breach",
    fix: "The model needs work. Right now the output filter is the only layer holding.",
  },
];

export function ProblemSection() {
  return (
    <section aria-labelledby="problem-title" className="border-b border-ink-700 py-20 sm:py-28">
      <div className="page-x">
        <SectionHeading index="01" eyebrow="The problem" id="problem-title" title={<>“Blocked” only tells you half the story.</>}>
          <p>
            Quick security checks usually record one result per attempt. But a block can mean two very different things,
            and each calls for a different fix.
          </p>
        </SectionHeading>

        <div className="mt-14 grid gap-px overflow-hidden rounded-[4px] border border-ink-600 bg-ink-600 lg:grid-cols-2">
          {RUNS.map((run) => (
            <article key={run.name} className="flex flex-col bg-ink-900">
              <div className="flex items-baseline justify-between gap-4 border-b border-ink-700 px-5 py-4 sm:px-7">
                <h3 className="font-mono text-[0.875rem] uppercase tracking-[0.12em] text-bone-100">{run.name}</h3>
                <p className="text-[0.875rem] text-bone-300">
                  Single-field result: <span className="font-semibold text-bone-50">Blocked</span>
                </p>
              </div>

              <ol className="grid border-b border-ink-700 sm:grid-cols-3" aria-label={`${run.name} stages`}>
                {run.stages.map((stage, index) => (
                  <li
                    key={stage.label}
                    className={`flex items-center justify-between gap-3 px-5 py-3 sm:flex-col sm:items-start sm:justify-start sm:gap-2 sm:py-5 ${index > 0 ? "border-t border-ink-700 sm:border-l sm:border-t-0" : ""}`}
                  >
                    <span className="text-[0.875rem] text-bone-300">{stage.label}</span>
                    <span>
                      <StatusChip tone={stage.tone}>{stage.status}</StatusChip>
                    </span>
                  </li>
                ))}
              </ol>

              <div className="flex flex-1 flex-col gap-6 px-5 py-6 sm:px-7">
                <p className="text-xl font-medium leading-snug text-bone-50">{run.story}</p>
                <div className="mt-auto grid gap-5 sm:grid-cols-2">
                  <Verdict heading="Model outcome" outcome={run.model} />
                  <p className="text-[0.9375rem] leading-relaxed text-bone-200">{run.fix}</p>
                </div>
              </div>
            </article>
          ))}
        </div>

        <p className="mt-10 max-w-3xl text-xl leading-relaxed text-bone-100 lg:ml-[calc(25%+0.625rem)]">
          BreachLens keeps <span className="text-bone-50 underline decoration-signal decoration-2 underline-offset-[6px]">model resilience</span>{" "}
          and <span className="text-bone-50 underline decoration-guard decoration-2 underline-offset-[6px]">system defense</span> as
          separate results, so a guardrail never hides a vulnerable model.
        </p>
      </div>
    </section>
  );
}
