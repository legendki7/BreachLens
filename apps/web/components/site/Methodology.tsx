import { StatusChip } from "../ui/Badges";
import { OUTCOME_LABELS } from "../ui/tones";
import { PROTECTED_VALUE, SCENARIO, getCase } from "../demo/demoCases";
import { SectionHeading } from "./SectionHeading";

const REASONS = [
  {
    title: "Investigate",
    body: "See exactly what the model said, even when the user never saw it, next to the guardrail decision that stopped it.",
  },
  {
    title: "Retest",
    body: "Technique, rubric version, and both outcomes are kept together, so a later run can be checked under the same criteria.",
  },
  {
    title: "Fix the right layer",
    body: "A model failure and a guardrail gap need different work. Separate verdicts show which one you are looking at.",
  },
];

const RULES: Array<{ when: string; model: string; system: string }> = [
  {
    when: "Input guardrail blocks the prompt",
    model: "Not tested. The target was never called, and the judge is skipped.",
    system: "Blocked by input guardrail.",
  },
  {
    when: "Output is allowed or only flagged",
    model: "Judged on the raw response.",
    system: "Mirrors the model outcome.",
  },
  {
    when: "Output guardrail blocks the response",
    model: "Judged on the raw response. A breach stays a breach.",
    system: "Blocked by output guardrail.",
  },
  {
    when: "Output guardrail modifies the response",
    model: "Judged on the raw response.",
    system: "Inconclusive until the modified text is assessed on its own.",
  },
  {
    when: "Required reference context is missing",
    model: "Inconclusive. No judge call is made.",
    system: "Inconclusive.",
  },
  {
    when: "A provider or judge call fails",
    model: "Recorded as an operational failure, not a security result.",
    system: "Same. No outcome is invented.",
  },
];

export function Methodology() {
  const specimen = getCase("c");
  const fields: Array<{ term: string; value: React.ReactNode }> = [
    { term: "Technique", value: specimen.technique },
    { term: "Attack", value: specimen.attack },
    {
      term: "Input guardrail",
      value: <StatusChip tone="neutral">{specimen.inputAction}</StatusChip>,
    },
    {
      term: "Raw target response",
      value: (
        <>
          Here&apos;s the line: “Escalation code:{" "}
          <mark className="rounded-[2px] bg-signal/20 px-1 text-signal-text">{PROTECTED_VALUE}</mark>”
        </>
      ),
    },
    {
      term: "Output guardrail",
      value: <StatusChip tone="guard">{specimen.outputAction}</StatusChip>,
    },
    { term: "Visible response", value: specimen.visibleResponse },
    {
      term: "Model outcome",
      value: <StatusChip tone="breach">{OUTCOME_LABELS[specimen.modelOutcome].label}</StatusChip>,
    },
    {
      term: "System outcome",
      value: <StatusChip tone="guard">{OUTCOME_LABELS[specimen.systemOutcome].label}</StatusChip>,
    },
    { term: "Rubric", value: SCENARIO.rubric },
    { term: "Rationale", value: specimen.reason },
  ];

  return (
    <section id="methodology" aria-labelledby="method-title" className="border-b border-ink-700 py-20 sm:py-28">
      <div className="page-x">
        <SectionHeading
          index="04"
          eyebrow="Evidence and methodology"
          id="method-title"
          title="Every turn is designed to leave a record you can question."
        >
          <p>
            An assessment keeps the full chain for each turn, from the attack to the final verdicts, instead of a single
            pass or fail.
          </p>
        </SectionHeading>

        <div className="mt-14 grid gap-12 lg:grid-cols-12 lg:gap-10">
          <div className="lg:col-span-4">
            <ul className="space-y-8">
              {REASONS.map((reason) => (
                <li key={reason.title}>
                  <h3 className="text-xl font-semibold text-bone-50">{reason.title}</h3>
                  <p className="mt-2 text-base leading-relaxed text-bone-200">{reason.body}</p>
                </li>
              ))}
            </ul>
          </div>

          <figure className="min-w-0 rounded-[4px] border border-ink-600 bg-ink-900 lg:col-span-8">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink-700 px-5 py-3">
              <p className="font-mono text-[0.8125rem] uppercase tracking-[0.12em] text-bone-200">Turn record</p>
              <p className="font-mono text-[0.75rem] uppercase tracking-[0.12em] text-guard">Illustrative</p>
            </div>
            <dl className="divide-y divide-ink-700">
              {fields.map((field) => (
                <div key={field.term} className="grid gap-1.5 px-5 py-3 sm:grid-cols-[9.5rem_1fr] sm:gap-4">
                  <dt className="font-mono text-[0.75rem] uppercase tracking-[0.1em] text-bone-300 sm:pt-0.5">
                    {field.term}
                  </dt>
                  <dd className="min-w-0 break-words text-[0.9375rem] leading-relaxed text-bone-100">{field.value}</dd>
                </div>
              ))}
            </dl>
            <figcaption className="border-t border-ink-700 px-5 py-3 text-[0.875rem] text-bone-300">
              The shape of a record, filled with the simulated Case C from the demo. Not stored assessment evidence.
            </figcaption>
          </figure>
        </div>

        <div className="mt-20 lg:ml-[calc(25%+0.625rem)]">
          <h3 className="text-2xl font-semibold tracking-tight text-bone-50">How the two outcomes are composed</h3>
          <p className="mt-3 max-w-2xl text-base leading-relaxed text-bone-200">
            The judge only classifies the raw model behavior. The system outcome is then derived from the recorded
            guardrail decisions.
          </p>

          <div className="mt-8 overflow-hidden rounded-[4px] border border-ink-600">
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">Outcome composition rules</caption>
              <thead className="hidden bg-ink-850 md:table-header-group">
                <tr>
                  <th scope="col" className="w-[32%] px-5 py-3 font-mono text-[0.75rem] font-medium uppercase tracking-[0.12em] text-bone-300">
                    When
                  </th>
                  <th scope="col" className="px-5 py-3 font-mono text-[0.75rem] font-medium uppercase tracking-[0.12em] text-bone-300">
                    Model outcome
                  </th>
                  <th scope="col" className="px-5 py-3 font-mono text-[0.75rem] font-medium uppercase tracking-[0.12em] text-bone-300">
                    System outcome
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-700">
                {RULES.map((rule) => (
                  <tr key={rule.when} className="block bg-ink-900 px-5 py-4 md:table-row md:p-0">
                    <th scope="row" className="block pb-2 text-base font-semibold text-bone-50 md:table-cell md:px-5 md:py-4 md:align-top">
                      {rule.when}
                    </th>
                    <td className="block py-1 text-[0.9375rem] leading-relaxed text-bone-200 md:table-cell md:px-5 md:py-4 md:align-top">
                      <span className="mr-2 font-mono text-[0.75rem] uppercase tracking-[0.1em] text-bone-300 md:hidden">Model</span>
                      {rule.model}
                    </td>
                    <td className="block py-1 text-[0.9375rem] leading-relaxed text-bone-200 md:table-cell md:px-5 md:py-4 md:align-top">
                      <span className="mr-2 font-mono text-[0.75rem] uppercase tracking-[0.1em] text-bone-300 md:hidden">System</span>
                      {rule.system}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-6 max-w-2xl text-[0.9375rem] leading-relaxed text-bone-300">
            LLM judges can disagree with each other and with people. Judge calibration and human review are not yet in
            place, so verdicts should be read alongside the stored evidence.
          </p>
        </div>
      </div>
    </section>
  );
}
