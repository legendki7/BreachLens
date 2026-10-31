"use client";

import { useEffect, useId, useReducer, useState, type KeyboardEvent, type ReactNode } from "react";

import { StatusChip, Verdict } from "../ui/Badges";
import { OUTCOME_LABELS, cx } from "../ui/tones";
import {
  DEMO_CASES,
  PROTECTED_VALUE,
  SCENARIO,
  STAGES,
  getCase,
  type DemoCase,
  type StageId,
  type TechnicalItem,
} from "./demoCases";
import { STAGE_COUNT, initialPlayback, playbackReducer, type PlaybackStatus } from "./playback";

const DEMO_LABEL = "Illustrative demo — simulated data, no live model calls.";
const EVALUATION_STEP = STAGES.findIndex((stage) => stage.id === "evaluation");
const SECONDARY_CONTROL =
  "btn-secondary gap-1.5 whitespace-nowrap px-3 sm:gap-2 sm:px-4 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-ink-500 disabled:hover:bg-transparent";
const LABEL = "font-mono text-[0.75rem] uppercase tracking-[0.12em] text-bone-200";

function isEditable(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || target.closest("input, textarea, select, [contenteditable]") !== null;
}

export function AssessmentDemo() {
  const [state, dispatch] = useReducer(playbackReducer, DEMO_CASES[0].id, initialPlayback);
  // Timeline visibility is view state only; toggling it never touches playback.
  const [timelineOpen, setTimelineOpen] = useState(false);
  const timelineId = useId();
  const demoCase = getCase(state.caseId);
  const shownStep = state.inspected ?? state.step;
  const verdictsReady = state.step >= EVALUATION_STEP;

  // One timer per playing step. Any transition bumps `seq`, which clears this
  // timer; the reducer also ignores ticks whose `seq` is stale.
  useEffect(() => {
    if (state.status !== "playing" || state.step < 0) return;
    const seq = state.seq;
    const timer = window.setTimeout(
      () => dispatch({ type: "tick", seq }),
      STAGES[state.step].dwellMs,
    );
    return () => window.clearTimeout(timer);
  }, [state.status, state.seq, state.step]);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.altKey || event.ctrlKey || event.metaKey || event.defaultPrevented) return;
    if (isEditable(event.target)) return;
    const key = event.key.toLowerCase();
    if (key === "k") {
      event.preventDefault();
      dispatch({ type: "toggle" });
    } else if (key === "arrowright") {
      event.preventDefault();
      dispatch({ type: "next" });
    } else if (key === "r") {
      event.preventDefault();
      dispatch({ type: "restart" });
    }
  }

  return (
    <div
      data-demo-root
      onKeyDown={onKeyDown}
      className="rounded-[4px] border border-ink-600 bg-ink-900 shadow-[0_40px_80px_-40px_rgba(0,0,0,0.8)]"
    >
      <FrameHeader />

      <CaseSelector
        selected={state.caseId}
        onSelect={(caseId) => dispatch({ type: "selectCase", caseId })}
      />

      <ScenarioStrip />

      <div className="border-b border-ink-700 px-4 py-4 sm:px-6">
        <p className="text-base leading-relaxed text-bone-100">
          <span className="font-semibold text-bone-50">
            Case {demoCase.letter}: {demoCase.title}.
          </span>{" "}
          {demoCase.description}
        </p>
        {demoCase.note ? (
          <p className="mt-3 border-l-2 border-guard/70 pl-3 text-[0.9375rem] leading-relaxed text-bone-200">
            {demoCase.note}
          </p>
        ) : null}
      </div>

      <Controls
        demoCase={demoCase}
        status={state.status}
        step={state.step}
        seq={state.seq}
        timelineId={timelineId}
        timelineOpen={timelineOpen}
        onToggleTimeline={() => setTimelineOpen((open) => !open)}
        onToggle={() => dispatch({ type: "toggle" })}
        onRestart={() => dispatch({ type: "restart" })}
        onNext={() => dispatch({ type: "next" })}
      />

      <div className="grid lg:grid-cols-[minmax(0,19rem)_minmax(0,1fr)]">
        <Timeline
          id={timelineId}
          open={timelineOpen}
          demoCase={demoCase}
          step={state.step}
          shownStep={shownStep}
          onInspect={(step) => dispatch({ type: "inspect", step })}
        />

        <div className="flex min-w-0 flex-col lg:border-l lg:border-ink-700">
          <div className="flex-1 px-4 py-5 sm:px-6 lg:min-h-[25rem] lg:py-6">
            {state.inspected !== null ? (
              <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.9375rem] text-bone-200">
                <span>
                  Viewing step {state.inspected + 1}. Playback is at step {state.step + 1}.
                </span>
                <button
                  type="button"
                  onClick={() => dispatch({ type: "inspect", step: state.step })}
                  className="font-medium text-bone-50 underline decoration-ink-400 underline-offset-4 hover:decoration-bone-100"
                >
                  Back to current step
                </button>
              </div>
            ) : null}

            {shownStep < 0 ? (
              <IntroPanel demoCase={demoCase} />
            ) : (
              <div key={`${demoCase.id}-${shownStep}`} className="stage-in">
                <StageDetail stageId={STAGES[shownStep].id} demoCase={demoCase} />
              </div>
            )}
          </div>

          <VerdictBar demoCase={demoCase} ready={verdictsReady} />
        </div>
      </div>

      <p className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement(demoCase, state.step, state.status === "finished")}
      </p>
    </div>
  );
}

function announcement(demoCase: DemoCase, step: number, finished: boolean): string {
  if (step < 0) return "";
  const stage = STAGES[step];
  const status = demoCase.stages[stage.id].status;
  const base = `Step ${step + 1} of ${STAGE_COUNT}, ${stage.label}: ${status}.`;
  if (!finished) return base;
  return `${base} Finished. Model outcome: ${OUTCOME_LABELS[demoCase.modelOutcome].label}. System outcome: ${OUTCOME_LABELS[demoCase.systemOutcome].label}.`;
}

function FrameHeader() {
  return (
    <div className="flex flex-col gap-2.5 rounded-t-[4px] border-b border-ink-700 bg-ink-850 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
      <p className="font-mono text-[0.8125rem] uppercase tracking-[0.12em] text-bone-100">Assessment walkthrough</p>
      <p className="inline-flex items-start gap-2 self-start rounded-[3px] border border-guard/40 bg-guard/10 px-2.5 py-1 text-[0.875rem] font-medium leading-snug text-guard sm:items-center sm:self-auto">
        <span aria-hidden="true" className="mt-[0.45em] h-1.5 w-1.5 shrink-0 rounded-full bg-guard sm:mt-0" />
        {DEMO_LABEL}
      </p>
    </div>
  );
}

function CaseSelector({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (caseId: string) => void;
}) {
  return (
    <fieldset className="border-b border-ink-700 px-4 pb-4 pt-3 sm:px-6">
      <legend className="sr-only">Choose a case</legend>
      <p aria-hidden="true" className="mb-2.5 text-[0.9375rem] text-bone-200">
        Choose a case
      </p>
      <div className="grid grid-cols-3 gap-2">
        {DEMO_CASES.map((item) => {
          const checked = item.id === selected;
          return (
            <label
              key={item.id}
              className={cx(
                "relative flex cursor-pointer flex-col items-start gap-1.5 rounded-[3px] border px-2.5 py-2.5 transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-bone-50 sm:flex-row sm:items-center sm:gap-3 sm:px-3",
                checked ? "border-bone-200 bg-ink-800" : "border-ink-600 hover:border-ink-400 hover:bg-ink-850",
              )}
            >
              <input
                type="radio"
                name="demo-case"
                value={item.id}
                checked={checked}
                onChange={() => onSelect(item.id)}
                aria-label={`Case ${item.letter}: ${item.title}`}
                className="sr-only"
              />
              <span
                aria-hidden="true"
                className={cx(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-[2px] font-mono text-[0.8125rem] font-semibold",
                  checked ? "bg-signal text-white" : "bg-ink-700 text-bone-100",
                )}
              >
                {item.letter}
              </span>
              <span
                aria-hidden="true"
                className={cx("text-[0.875rem] font-medium leading-snug sm:text-[0.9375rem]", checked ? "text-bone-50" : "text-bone-200")}
              >
                <span className="md:hidden">{item.shortTitle}</span>
                <span className="hidden md:inline">{item.title}</span>
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function ScenarioStrip() {
  return (
    <dl className="grid grid-cols-2 gap-x-5 gap-y-3 border-b border-ink-700 bg-ink-950/40 px-4 py-4 sm:px-6 xl:grid-cols-[1fr_1.15fr_1.3fr_0.9fr]">
      <div className="min-w-0">
        <dt className={LABEL}>Scenario</dt>
        <dd className="mt-1 text-[0.9375rem] leading-snug text-bone-50">{SCENARIO.name}</dd>
      </div>
      <div className="min-w-0">
        <dt className={LABEL}>Target</dt>
        <dd className="mt-1 text-[0.9375rem] leading-snug text-bone-50">{SCENARIO.target}</dd>
      </div>
      <div className="min-w-0">
        <dt className={LABEL}>Protected test value</dt>
        <dd className="mt-1 text-[0.9375rem] leading-snug text-bone-50">
          <code className="font-mono">{PROTECTED_VALUE}</code>
          <span className="mt-0.5 block text-[0.875rem] text-bone-200">Fictional, not a real credential</span>
        </dd>
      </div>
      <div className="min-w-0">
        <dt className={LABEL}>Guardrail policy</dt>
        <dd className="mt-1 text-[0.9375rem] leading-snug text-bone-50">{SCENARIO.policy}</dd>
      </div>
    </dl>
  );
}

function Controls({
  demoCase,
  status,
  step,
  seq,
  timelineId,
  timelineOpen,
  onToggleTimeline,
  onToggle,
  onRestart,
  onNext,
}: {
  demoCase: DemoCase;
  status: PlaybackStatus;
  step: number;
  seq: number;
  timelineId: string;
  timelineOpen: boolean;
  onToggleTimeline: () => void;
  onToggle: () => void;
  onRestart: () => void;
  onNext: () => void;
}) {
  const playing = status === "playing";
  const playLabel = playing ? "Pause" : status === "finished" ? "Replay" : status === "paused" ? "Resume" : "Play";
  const current = step >= 0 ? STAGES[step] : null;
  const currentInfo = current ? demoCase.stages[current.id] : null;
  const progressText = current
    ? `Step ${step + 1} of ${STAGE_COUNT} — ${current.label}`
    : `Ready — ${STAGE_COUNT} stages`;
  const stateText = status === "finished" ? "Finished" : status === "paused" ? "Paused" : null;

  return (
    <div className="border-b border-ink-700 bg-ink-850 px-4 py-4 sm:px-6">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <div className="grid w-full grid-cols-3 gap-2 sm:flex sm:w-auto sm:items-center">
          <button
            type="button"
            onClick={onToggle}
            className="btn-primary gap-1.5 whitespace-nowrap px-3 sm:min-w-[7.5rem] sm:gap-2 sm:px-5"
            aria-label={`${playLabel} walkthrough`}
          >
            {playing ? <PauseIcon /> : status === "finished" ? <ReplayIcon /> : <PlayIcon />}
            {playLabel}
          </button>
          <button
            type="button"
            onClick={onNext}
            disabled={status === "finished"}
            aria-label="Next step"
            className={SECONDARY_CONTROL}
          >
            <NextIcon />
            <span className="sm:hidden">Next</span>
            <span className="hidden sm:inline">Next step</span>
          </button>
          <button type="button" onClick={onRestart} disabled={step < 0} className={SECONDARY_CONTROL}>
            <ReplayIcon />
            Restart
          </button>
        </div>
        <p className="hidden text-[0.875rem] text-bone-200 lg:ml-auto lg:block">
          Keys: <kbd className="font-mono text-bone-50">K</kbd> play/pause · <kbd className="font-mono text-bone-50">→</kbd>{" "}
          next · <kbd className="font-mono text-bone-50">R</kbd> restart
        </p>
      </div>

      <div
        className="mt-4 flex gap-1"
        role="progressbar"
        aria-label="Walkthrough progress"
        aria-valuemin={0}
        aria-valuemax={STAGE_COUNT}
        aria-valuenow={Math.max(step + 1, 0)}
        aria-valuetext={`${progressText}${stateText ? `, ${stateText.toLowerCase()}` : ""}`}
      >
        {STAGES.map((stage, index) => (
          <span key={stage.id} className="relative h-1.5 flex-1 overflow-hidden rounded-[1px] bg-ink-600">
            {index <= step ? (
              <span className={cx("absolute inset-0", index === step ? "bg-signal" : "bg-bone-300")} />
            ) : null}
            {playing && index === step + 1 ? (
              <span
                key={seq}
                className="step-fill absolute inset-0 bg-bone-400/60"
                style={{ animationDuration: `${STAGES[step].dwellMs}ms` }}
              />
            ) : null}
          </span>
        ))}
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <p className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
          <span className="text-[0.9375rem] font-semibold text-bone-50">{progressText}</span>
          {currentInfo ? <StatusChip tone={currentInfo.tone}>{currentInfo.status}</StatusChip> : null}
          {stateText ? <span className="text-[0.875rem] text-bone-200">{stateText}</span> : null}
        </p>
        <button
          type="button"
          onClick={onToggleTimeline}
          aria-expanded={timelineOpen}
          aria-controls={timelineId}
          className="inline-flex min-h-10 items-center gap-1.5 rounded-[3px] px-1 text-[0.9375rem] font-medium text-bone-50 underline decoration-ink-400 underline-offset-4 hover:decoration-bone-100 lg:hidden"
        >
          {timelineOpen ? "Hide steps" : "View all steps"}
          <Chevron open={timelineOpen} />
        </button>
      </div>
    </div>
  );
}

function Timeline({
  id,
  open,
  demoCase,
  step,
  shownStep,
  onInspect,
}: {
  id: string;
  open: boolean;
  demoCase: DemoCase;
  step: number;
  shownStep: number;
  onInspect: (step: number) => void;
}) {
  return (
    <nav
      id={id}
      aria-label="Assessment stages"
      className={cx(
        "border-b border-ink-700 bg-ink-850/60 px-3 py-3 sm:px-4 lg:block lg:border-b-0 lg:py-4",
        open ? "block" : "hidden",
      )}
    >
      <ol className="relative">
        {STAGES.map((stage, index) => {
          const revealed = index <= step;
          const current = index === step;
          const shown = index === shownStep;
          const info = demoCase.stages[stage.id];
          return (
            <li key={stage.id} className="relative">
              {index < STAGES.length - 1 ? (
                <span
                  aria-hidden="true"
                  className={cx(
                    "absolute left-[1.3rem] top-10 h-[calc(100%-1.75rem)] w-px",
                    index < step ? "bg-bone-300" : "bg-ink-600",
                  )}
                />
              ) : null}
              <button
                type="button"
                disabled={!revealed}
                aria-current={current ? "step" : undefined}
                aria-label={`Step ${index + 1}, ${stage.label}: ${revealed ? info.status : "waiting"}`}
                onClick={() => onInspect(index)}
                className={cx(
                  "relative flex w-full items-start gap-3 rounded-[3px] px-2 py-2.5 text-left transition-colors",
                  shown && revealed ? "bg-ink-700" : revealed && "hover:bg-ink-800",
                  !revealed && "cursor-default",
                )}
              >
                <span
                  aria-hidden="true"
                  className={cx(
                    "relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-[2px] font-mono text-[0.75rem] font-semibold",
                    current
                      ? "bg-signal text-white"
                      : revealed
                        ? "bg-bone-100 text-ink-950"
                        : "border border-ink-500 bg-ink-850 text-bone-300",
                  )}
                >
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
                    <span className={cx("text-[0.9375rem] font-semibold", revealed ? "text-bone-50" : "text-bone-300")}>
                      {stage.label}
                    </span>
                    {revealed ? (
                      <StatusChip tone={info.tone}>{info.status}</StatusChip>
                    ) : (
                      <StatusChip tone="pending">Waiting</StatusChip>
                    )}
                  </span>
                  {revealed ? (
                    <span className="mt-1 block text-[0.9375rem] leading-snug text-bone-200">{info.summary}</span>
                  ) : null}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function IntroPanel({ demoCase }: { demoCase: DemoCase }) {
  return (
    <div className="flex h-full flex-col justify-center">
      <p className="eyebrow">Ready</p>
      <h3 className="mt-3 text-2xl font-semibold tracking-tight text-bone-50">
        Case {demoCase.letter}: {demoCase.title}
      </h3>
      <p className="mt-3 max-w-xl text-base leading-relaxed text-bone-100">
        Press Play to watch the turn move through all six stages, or use Next step to go one stage at a time. Select any
        completed stage to inspect it.
      </p>
      <p className="mt-4 max-w-xl text-[0.9375rem] leading-relaxed text-bone-200">{DEMO_LABEL}</p>
    </div>
  );
}

function Excerpt({
  label,
  children,
  variant = "default",
}: {
  label: string;
  children: ReactNode;
  variant?: "default" | "withheld" | "muted";
}) {
  return (
    <figure className="min-w-0">
      <figcaption className={LABEL}>{label}</figcaption>
      <blockquote
        className={cx(
          "mt-2 break-words rounded-[3px] border px-4 py-3 font-mono text-[0.9375rem] leading-[1.65]",
          variant === "default" && "border-ink-500 bg-ink-950 text-bone-50",
          variant === "muted" && "border-ink-600 bg-ink-950/60 text-bone-100",
          variant === "withheld" && "border-dashed border-guard/50 bg-guard/[0.06] italic text-bone-100",
        )}
      >
        {children}
      </blockquote>
    </figure>
  );
}

function withProtectedValue(text: string): ReactNode {
  const parts = text.split(PROTECTED_VALUE);
  if (parts.length === 1) return text;
  return parts.flatMap((part, index) =>
    index === 0
      ? [part]
      : [
          <mark key={index} className="rounded-[2px] bg-signal/20 px-1 not-italic text-signal-text">
            {PROTECTED_VALUE}
            <span className="sr-only"> (protected value disclosed)</span>
          </mark>,
          part,
        ],
  );
}

function TechnicalDetails({ items }: { items: TechnicalItem[] }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  if (items.length === 0) return null;
  return (
    <div className="mt-6 border-t border-ink-700 pt-4">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex min-h-10 items-center gap-2 rounded-[3px] text-[0.9375rem] font-medium text-bone-100 hover:text-bone-50"
      >
        <Chevron open={open} />
        Technical details
      </button>
      <dl
        id={id}
        className={cx(
          "mt-2 gap-3 rounded-[3px] border border-ink-600 bg-ink-950/50 px-4 py-3",
          open ? "grid" : "hidden",
        )}
      >
        {items.map((item) => (
          <div key={item.term} className="grid gap-1 sm:grid-cols-[8.5rem_1fr] sm:gap-4">
            <dt className={cx(LABEL, "sm:pt-0.5")}>{item.term}</dt>
            <dd className="text-[0.9375rem] leading-relaxed text-bone-100">{item.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function SkippedNote({ children }: { children: ReactNode }) {
  return (
    <p className="mt-4 rounded-[3px] border border-dashed border-ink-400 px-4 py-3 text-base leading-relaxed text-bone-100">
      {children}
    </p>
  );
}

function StageDetail({ stageId, demoCase }: { stageId: StageId; demoCase: DemoCase }) {
  const info = demoCase.stages[stageId];
  const label = STAGES.find((stage) => stage.id === stageId)?.label ?? stageId;
  const skipped = info.tone === "skipped" && stageId !== "evaluation";

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-xl font-semibold tracking-tight text-bone-50">{label}</h3>
        <StatusChip tone={info.tone}>{info.status}</StatusChip>
      </div>

      {skipped ? (
        <SkippedNote>{info.explanation}</SkippedNote>
      ) : (
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-bone-100 sm:text-[1.0625rem]">{info.explanation}</p>
      )}

      {info.caveat ? (
        <p className="mt-3 max-w-2xl border-l-2 border-guard/70 pl-3 text-[0.9375rem] leading-relaxed text-bone-200">
          {info.caveat}
        </p>
      ) : null}

      <StageBody stageId={stageId} demoCase={demoCase} />
      <TechnicalDetails items={info.technical} />
    </div>
  );
}

function StageBody({ stageId, demoCase }: { stageId: StageId; demoCase: DemoCase }) {
  switch (stageId) {
    case "attack":
      return (
        <div className="mt-5">
          <Excerpt label="Test prompt">{demoCase.attack}</Excerpt>
          <p className="mt-2 text-[0.9375rem] text-bone-200">Technique: {demoCase.technique}</p>
        </div>
      );

    case "input":
      return null;

    case "target":
      return demoCase.rawResponse ? (
        <div className="mt-5">
          <Excerpt label="Raw reply · what the model said">{withProtectedValue(demoCase.rawResponse)}</Excerpt>
        </div>
      ) : null;

    case "output":
      return demoCase.rawResponse ? (
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <Excerpt label="Raw reply" variant="muted">
            {withProtectedValue(demoCase.rawResponse)}
          </Excerpt>
          <Excerpt label="Visible response · what the user sees" variant={demoCase.visibleWithheld ? "withheld" : "default"}>
            {demoCase.visibleResponse}
          </Excerpt>
        </div>
      ) : null;

    case "evaluation":
      return (
        <ul className="mt-5 max-w-2xl divide-y divide-ink-700 border-y border-ink-700">
          {demoCase.checks.map((check) => (
            <li key={check.label} className="flex items-center justify-between gap-3 py-2.5">
              <span className="text-[0.9375rem] text-bone-100">{check.label}</span>
              <StatusChip tone={check.tone}>{check.result}</StatusChip>
            </li>
          ))}
        </ul>
      );

    case "evidence":
      return (
        <div className="mt-5">
          <p className="text-[0.9375rem] text-bone-200">Illustrative record. Simulated, not stored evidence.</p>
          <dl className="mt-3 grid gap-x-6 gap-y-4 sm:grid-cols-2">
            <RecordField term="Test prompt" mono>
              {demoCase.attack}
            </RecordField>
            <RecordField term="Raw reply" mono>
              {demoCase.rawResponse ? withProtectedValue(demoCase.rawResponse) : "None. The target was not called."}
            </RecordField>
            <RecordField term="Input check">{demoCase.inputAction}</RecordField>
            <RecordField term="Output check">{demoCase.outputAction}</RecordField>
            <RecordField term="Visible response" mono>
              {demoCase.visibleResponse}
            </RecordField>
            <RecordField term="Outcomes">
              Model: {OUTCOME_LABELS[demoCase.modelOutcome].label}
              <br />
              System: {OUTCOME_LABELS[demoCase.systemOutcome].label}
            </RecordField>
          </dl>
        </div>
      );
  }
}

function RecordField({ term, mono = false, children }: { term: string; mono?: boolean; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className={LABEL}>{term}</dt>
      <dd
        className={cx(
          "mt-1 break-words leading-relaxed text-bone-100",
          mono ? "font-mono text-[0.875rem]" : "text-[0.9375rem]",
        )}
      >
        {children}
      </dd>
    </div>
  );
}

function VerdictBar({ demoCase, ready }: { demoCase: DemoCase; ready: boolean }) {
  return (
    <div className="grid gap-5 rounded-b-[4px] border-t border-ink-700 bg-ink-850 px-4 py-5 sm:grid-cols-2 sm:px-6">
      <div>
        <Verdict heading="Model outcome" outcome={ready ? demoCase.modelOutcome : "pending"} />
        <p className="mt-1.5 text-[0.9375rem] text-bone-200">How the target itself behaved</p>
      </div>
      <div>
        <Verdict heading="System outcome" outcome={ready ? demoCase.systemOutcome : "pending"} />
        <p className="mt-1.5 text-[0.9375rem] text-bone-200">What the guardrails let through</p>
      </div>
    </div>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 16 16"
      className={cx("h-4 w-4 transition-transform duration-150", open && "rotate-180")}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
    >
      <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" className="h-4 w-4" fill="currentColor">
      <path d="M4 2.5v11l9-5.5-9-5.5Z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" className="h-4 w-4" fill="currentColor">
      <path d="M4 2.5h3v11H4zM9 2.5h3v11H9z" />
    </svg>
  );
}

function NextIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" className="h-4 w-4" fill="currentColor">
      <path d="M3 2.5v11l7-5.5-7-5.5ZM11 2.5h2v11h-2z" />
    </svg>
  );
}

function ReplayIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3.5 8a4.5 4.5 0 1 0 1.3-3.2" strokeLinecap="round" />
      <path d="M3 2.5v3h3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
