import { SectionHeading } from "./SectionHeading";

const AUDIENCES = [
  {
    who: "Teams building LLM applications",
    need: "You need to know whether your system prompt and guardrails hold up before release.",
    benefit:
      "Run scenarios such as hidden-context exposure and prompt injection against your target, and see which layer did the work when an attack failed.",
  },
  {
    who: "Security testing teams",
    need: "Manual red-teaming produces findings that are hard to review or repeat.",
    benefit:
      "Keep each attempt's prompt, raw response, guardrail decisions, and verdicts together, so a finding can be checked and rerun.",
  },
  {
    who: "Researchers",
    need: "Comparing model behavior is only meaningful under the same conditions.",
    benefit:
      "Run the same scenario and rubric version against different models, with model behavior kept apart from the defenses around it.",
  },
];

export function Audience() {
  return (
    <section aria-labelledby="audience-title" className="border-b border-ink-700 py-20 sm:py-28">
      <div className="page-x">
        <SectionHeading index="05" eyebrow="Who it is for" id="audience-title" title="Built for people who have to explain a result, not just report one." />

        <ul className="mt-14 border-b border-ink-700 lg:ml-[calc(25%+0.625rem)]">
          {AUDIENCES.map((audience) => (
            <li key={audience.who} className="grid gap-4 border-t border-ink-700 py-8 md:grid-cols-[minmax(0,15rem)_minmax(0,1fr)] md:gap-10">
              <h3 className="text-xl font-semibold leading-snug text-bone-50">{audience.who}</h3>
              <div>
                <p className="text-base leading-relaxed text-bone-300">{audience.need}</p>
                <p className="mt-2 text-lg leading-relaxed text-bone-100">{audience.benefit}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
