import { AssessmentDemo } from "../demo/AssessmentDemo";
import { SectionHeading } from "./SectionHeading";

export function DemoSection() {
  return (
    <section id="demo" aria-labelledby="demo-title" className="border-b border-ink-700 bg-ink-950 py-20 sm:py-28">
      <div className="page-x">
        <SectionHeading index="03" eyebrow="Interactive demo" id="demo-title" title="Walk through one turn, stage by stage.">
          <p>
            Three short cases against a fictional support assistant. Each one runs the same six stages and ends with
            separate model and system verdicts. The data is simulated to show how the workflow is designed to behave.
          </p>
        </SectionHeading>

        <div className="mt-12">
          <AssessmentDemo />
        </div>
      </div>
    </section>
  );
}
