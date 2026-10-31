import { Audience } from "../components/site/Audience";
import { DemoSection } from "../components/site/DemoSection";
import { Hero } from "../components/site/Hero";
import { HowItWorks } from "../components/site/HowItWorks";
import { Methodology } from "../components/site/Methodology";
import { ProblemSection } from "../components/site/ProblemSection";
import { ProjectStatus } from "../components/site/ProjectStatus";
import { SiteFooter } from "../components/site/SiteFooter";
import { SiteHeader } from "../components/site/SiteHeader";

export default function Home() {
  return (
    <>
      <a
        href="#main"
        className="sr-only z-50 rounded-[3px] bg-bone-50 px-4 py-2 font-semibold text-ink-950 focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to content
      </a>
      <SiteHeader />
      <main id="main" tabIndex={-1} className="outline-none">
        <div id="top" />
        <Hero />
        <ProblemSection />
        <HowItWorks />
        <DemoSection />
        <Methodology />
        <Audience />
        <ProjectStatus />
      </main>
      <SiteFooter />
    </>
  );
}
