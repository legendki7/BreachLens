// Pure playback state machine for the illustrative assessment walkthrough.
// Kept free of React and of runtime imports so it can be unit-tested with
// Node's built-in test runner.

export const STAGE_COUNT = 6;
export const LAST_STEP = STAGE_COUNT - 1;

export type PlaybackStatus = "idle" | "playing" | "paused" | "finished";

export interface PlaybackState {
  caseId: string;
  /** Index of the latest revealed stage; -1 before the walkthrough starts. */
  step: number;
  status: PlaybackStatus;
  /** Revealed stage the viewer is inspecting; null follows the latest step. */
  inspected: number | null;
  /**
   * Incremented on every transition. A pending timer only advances playback
   * when its tick carries the current sequence number, so stale timers from a
   * previous case, step, or pause can never change the state.
   */
  seq: number;
}

export type PlaybackAction =
  | { type: "play" }
  | { type: "pause" }
  | { type: "toggle" }
  | { type: "next" }
  | { type: "restart" }
  | { type: "selectCase"; caseId: string }
  | { type: "inspect"; step: number }
  | { type: "tick"; seq: number };

export function initialPlayback(caseId: string): PlaybackState {
  return { caseId, step: -1, status: "idle", inspected: null, seq: 0 };
}

function moveTo(state: PlaybackState, step: number, status: PlaybackStatus): PlaybackState {
  return {
    ...state,
    step,
    status: step >= LAST_STEP ? "finished" : status,
    inspected: null,
    seq: state.seq + 1,
  };
}

export function playbackReducer(state: PlaybackState, action: PlaybackAction): PlaybackState {
  switch (action.type) {
    case "play":
      if (state.status === "playing") return state;
      if (state.status === "idle" || state.status === "finished") {
        return moveTo(state, 0, "playing");
      }
      return { ...state, status: "playing", inspected: null, seq: state.seq + 1 };

    case "pause":
      if (state.status !== "playing") return state;
      return { ...state, status: "paused", seq: state.seq + 1 };

    case "toggle":
      return playbackReducer(state, { type: state.status === "playing" ? "pause" : "play" });

    case "next":
      // Manual stepping always pauses automatic playback, so the two never race.
      if (state.status === "finished") return state;
      return moveTo(state, state.step + 1, "paused");

    case "restart":
      return moveTo(state, 0, "playing");

    case "selectCase":
      return { ...initialPlayback(action.caseId), seq: state.seq + 1 };

    case "inspect":
      if (action.step < 0 || action.step > state.step) return state;
      return { ...state, inspected: action.step === state.step ? null : action.step };

    case "tick":
      if (action.seq !== state.seq || state.status !== "playing") return state;
      return moveTo(state, state.step + 1, "playing");

    default:
      return state;
  }
}
