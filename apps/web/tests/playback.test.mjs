// Run with `npm test` (Node's built-in runner; Node 22.18+ strips TypeScript types).
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  LAST_STEP,
  initialPlayback,
  playbackReducer as reduce,
} from "../components/demo/playback.ts";

const run = (state, ...actions) => actions.reduce(reduce, state);
const tick = (state) => reduce(state, { type: "tick", seq: state.seq });

test("starts idle and does not autoplay", () => {
  const state = initialPlayback("a");
  assert.equal(state.status, "idle");
  assert.equal(state.step, -1);
});

test("play reveals the first stage and ticks advance to a finished state", () => {
  let state = run(initialPlayback("a"), { type: "play" });
  assert.deepEqual([state.status, state.step], ["playing", 0]);
  for (let i = 1; i <= LAST_STEP; i += 1) state = tick(state);
  assert.deepEqual([state.status, state.step], ["finished", LAST_STEP]);
  assert.equal(tick(state), state, "ticks after finishing are ignored");
});

test("stale ticks never advance playback", () => {
  const playing = run(initialPlayback("a"), { type: "play" });
  const staleSeq = playing.seq;
  const paused = reduce(playing, { type: "pause" });
  assert.equal(reduce(paused, { type: "tick", seq: staleSeq }), paused);

  const resumed = reduce(paused, { type: "play" });
  assert.equal(reduce(resumed, { type: "tick", seq: staleSeq }), resumed);
  assert.equal(tick(resumed).step, 1);
});

test("switching cases resets playback and invalidates the old timer", () => {
  const playing = run(initialPlayback("a"), { type: "play" });
  const switched = reduce(playing, { type: "selectCase", caseId: "c" });
  assert.deepEqual([switched.caseId, switched.status, switched.step], ["c", "idle", -1]);
  assert.equal(reduce(switched, { type: "tick", seq: playing.seq }), switched);
  assert.ok(switched.seq > playing.seq);
});

test("manual stepping pauses automatic playback", () => {
  const playing = run(initialPlayback("b"), { type: "play" });
  const stepped = reduce(playing, { type: "next" });
  assert.deepEqual([stepped.status, stepped.step], ["paused", 1]);
  assert.equal(reduce(stepped, { type: "tick", seq: playing.seq }), stepped);
});

test("next from idle reveals the first stage without playing", () => {
  const state = reduce(initialPlayback("b"), { type: "next" });
  assert.deepEqual([state.status, state.step], ["paused", 0]);
});

test("stepping to the last stage finishes, and next is then a no-op", () => {
  let state = initialPlayback("c");
  for (let i = 0; i <= LAST_STEP; i += 1) state = reduce(state, { type: "next" });
  assert.deepEqual([state.status, state.step], ["finished", LAST_STEP]);
  assert.equal(reduce(state, { type: "next" }), state);
});

test("restart and replay start again from the first stage", () => {
  const midway = run(initialPlayback("a"), { type: "next" }, { type: "next" }, { type: "next" });
  const restarted = reduce(midway, { type: "restart" });
  assert.deepEqual([restarted.status, restarted.step, restarted.caseId], ["playing", 0, "a"]);

  let finished = initialPlayback("a");
  for (let i = 0; i <= LAST_STEP; i += 1) finished = reduce(finished, { type: "next" });
  const replay = reduce(finished, { type: "play" });
  assert.deepEqual([replay.status, replay.step], ["playing", 0]);
});

test("inspecting is limited to revealed stages and clears on the next step", () => {
  const state = run(initialPlayback("a"), { type: "next" }, { type: "next" }, { type: "next" });
  assert.equal(reduce(state, { type: "inspect", step: 4 }), state, "cannot inspect unrevealed stages");
  const inspecting = reduce(state, { type: "inspect", step: 0 });
  assert.equal(inspecting.inspected, 0);
  assert.equal(reduce(inspecting, { type: "next" }).inspected, null);
});

test("toggle alternates between playing and paused", () => {
  const playing = reduce(initialPlayback("a"), { type: "toggle" });
  assert.equal(playing.status, "playing");
  assert.equal(reduce(playing, { type: "toggle" }).status, "paused");
});
