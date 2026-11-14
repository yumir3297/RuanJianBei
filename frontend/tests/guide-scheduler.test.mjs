import test from "node:test";
import assert from "node:assert/strict";
import { createGuideController, initialGuideState, reduceGuideState } from "../src/guide/scheduler.js";

test("safety event has priority, cancels generation and audio, and deduplicates", () => {
  let state = initialGuideState();
  state = reduceGuideState(state, { type: "enable" }).state;
  const raised = reduceGuideState(state, { type: "safety_raised", safetyEvent: { event_id: "alert-1", priority: 80 } });
  assert.equal(raised.state.status, "interrupted");
  assert.deepEqual(raised.effects, ["cancel_pending", "stop_audio", "show_safety"]);
  assert.equal(reduceGuideState(raised.state, { type: "safety_raised", safetyEvent: { event_id: "alert-1" } }).effects.length, 0);
});

test("late decision and user stop cannot restart narration", () => {
  let state = reduceGuideState(initialGuideState(), { type: "enable" }).state;
  const started = reduceGuideState(state, { type: "decision_started" });
  const generation = started.state.generation;
  state = reduceGuideState(started.state, { type: "user_stop" }).state;
  const late = reduceGuideState(state, { type: "decision_received", generation, action: "full_narration" });
  assert.equal(late.state.status, "idle");
  assert.equal(late.effects.includes("narrate"), false);
});

test("hiding the map suspends CASS and fences pending decisions", () => {
  let state = reduceGuideState(initialGuideState(), { type: "enable" }).state;
  state = reduceGuideState(state, { type: "map_active", active: true }).state;
  const started = reduceGuideState(state, { type: "decision_started" }).state;
  const hidden = reduceGuideState(started, { type: "map_active", active: false });
  assert.equal(hidden.state.status, "suspended");
  assert.equal(hidden.effects.includes("cancel_pending"), true);
  const late = reduceGuideState(hidden.state, { type: "decision_received", generation: started.generation, action: "full_narration" });
  assert.equal(late.state.status, "suspended");
  assert.equal(late.effects.includes("narrate"), false);
});

test("controller routes a safety event to the local notice before narration", async () => {
  const order = [];
  const controller = createGuideController({
    api: { decide: async () => ({ available: true, safety_events: [{ event_id: "sos", priority: 100 }] }) },
    effects: { show_safety: () => order.push("notice"), narrate: () => order.push("narrate") },
  });
  controller.dispatch({ type: "enable" });
  await controller.evaluate({});
  assert.deepEqual(order, ["notice"]);
  assert.equal(controller.getState().status, "interrupted");
});

test("a late safety response after CASS is disabled is discarded", async () => {
  let resolveDecision;
  const controller = createGuideController({ api: { decide: () => new Promise((resolve) => { resolveDecision = resolve; }) } });
  controller.dispatch({ type: "enable" });
  const pending = controller.evaluate({});
  controller.dispatch({ type: "disable" });
  resolveDecision({ available: true, safety_events: [{ event_id: "late-alert", priority: 80 }] });
  await pending;
  assert.equal(controller.getState().status, "off");
  assert.equal(controller.getState().activeSafetyEvent, null);
});

test("a still active event may be raised again after it was cleared for recheck", () => {
  let state = reduceGuideState(initialGuideState(), { type: "enable" }).state;
  state = reduceGuideState(state, { type: "safety_raised", safetyEvent: { event_id: "alert-1", priority: 80 } }).state;
  state = reduceGuideState(state, { type: "safety_cleared", eventId: "alert-1" }).state;
  const raised = reduceGuideState(state, { type: "safety_raised", safetyEvent: { event_id: "alert-1", priority: 80 } });
  assert.equal(raised.state.status, "interrupted");
});

test("a higher priority event replaces the current notice, while lower priority cannot", () => {
  let state = reduceGuideState(initialGuideState(), { type: "enable" }).state;
  state = reduceGuideState(state, { type: "safety_raised", safetyEvent: { event_id: "weather", priority: 80 } }).state;
  state = reduceGuideState(state, { type: "safety_raised", safetyEvent: { event_id: "zone", priority: 70 } }).state;
  assert.equal(state.activeSafetyEvent.event_id, "weather");
  state = reduceGuideState(state, { type: "safety_raised", safetyEvent: { event_id: "sos", priority: 100 } }).state;
  assert.equal(state.activeSafetyEvent.event_id, "sos");
});

test("an update for the active event refreshes its instructions without resuming narration", () => {
  let state = reduceGuideState(initialGuideState(), { type: "enable" }).state;
  state = reduceGuideState(state, { type: "safety_raised", safetyEvent: { event_id: "weather", priority: 80, instruction: "旧指引" } }).state;
  const updated = reduceGuideState(state, { type: "safety_raised", safetyEvent: { event_id: "weather", priority: 80, instruction: "最新指引" } });
  assert.equal(updated.state.status, "interrupted");
  assert.equal(updated.state.activeSafetyEvent.instruction, "最新指引");
  assert.deepEqual(updated.effects, ["show_safety"]);
});

test("a late decision is marked stale so callers cannot display its old suggestion", async () => {
  let resolveDecision;
  const controller = createGuideController({ api: { decide: () => new Promise((resolve) => { resolveDecision = resolve; }) } });
  controller.dispatch({ type: "enable" });
  const pending = controller.evaluate({});
  controller.dispatch({ type: "user_stop" });
  resolveDecision({ available: true, decision: { action: "full_narration" } });
  assert.equal((await pending).stale, true);
});

test("a context change cancels a pending assessment and fences its late response", async () => {
  let resolveDecision;
  const controller = createGuideController({
    api: { decide: () => new Promise(resolve => { resolveDecision = resolve; }) },
  });
  controller.dispatch({ type: "enable" });
  const pending = controller.evaluate({ tour_session_id: "tour-old" });
  controller.dispatch({ type: "context_changed" });
  resolveDecision({ available: true, decision: { action: "full_narration" } });

  const response = await pending;
  assert.equal(response.stale, true);
  assert.equal(controller.getState().status, "idle");
});
