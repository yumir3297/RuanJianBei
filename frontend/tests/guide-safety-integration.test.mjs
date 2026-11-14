import test from "node:test";
import assert from "node:assert/strict";
import { createPinia, setActivePinia } from "pinia";
import { useGuideSafetyStore } from "../src/stores/guideSafety.js";
import { createGuideController } from "../src/guide/scheduler.js";
import { createDemoScenarioController } from "../src/guide/scenario.js";

test("a simulated warning holds narration until acknowledgement and explicit resume", () => {
  setActivePinia(createPinia());
  const safety = useGuideSafetyStore();
  const controller = createGuideController();
  controller.subscribe(state => safety.observeControllerState(state));
  const demo = createDemoScenarioController({ dispatch: controller.dispatch });
  assert.equal(demo.start(), true);
  assert.equal(demo.raiseWarning(), true);
  assert.equal(safety.hold, true);
  assert.equal(safety.resumeDemo(), false);
  assert.equal(demo.acknowledge(), true);
  assert.equal(safety.hold, true);
  assert.equal(demo.resume(), true);
  assert.equal(safety.resumeDemo(), true);
  assert.equal(safety.hold, false);
});

test("acknowledging a real alert or losing its source does not clear the hold", () => {
  setActivePinia(createPinia());
  const safety = useGuideSafetyStore();
  const controller = createGuideController();
  controller.subscribe(state => safety.observeControllerState(state));
  controller.dispatch({ type: "enable" });
  controller.dispatch({ type: "safety_raised", safetyEvent: { event_id: "real", priority: 80, simulated: false } });
  controller.dispatch({ type: "safety_cleared", eventId: "real" });
  assert.equal(safety.hold, true);
  assert.equal(safety.resumeDemo(), false);
  controller.dispatch({ type: "dispose" });
  assert.equal(safety.hold, true);
});

test("a later simulated event cannot downgrade a real safety hold", () => {
  setActivePinia(createPinia());
  const safety = useGuideSafetyStore();
  safety.observeControllerState({ activeSafetyEvent: { event_id: "real", simulated: false } });
  safety.observeControllerState({ activeSafetyEvent: null });
  safety.observeControllerState({ activeSafetyEvent: { event_id: "demo", simulated: true } });
  safety.observeControllerState({ activeSafetyEvent: null });
  assert.equal(safety.resumeDemo(), false);
  assert.equal(safety.hold, true);
});

test("real safety hold survives reload in the same tab without persisting alert details", () => {
  const values = new Map();
  const previous = globalThis.sessionStorage;
  globalThis.sessionStorage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
  try {
    setActivePinia(createPinia());
    const first = useGuideSafetyStore();
    first.observeControllerState({ activeSafetyEvent: { event_id: 'private-alert', simulated: false } });
    assert.deepEqual([...values.values()], ['1']);
    setActivePinia(createPinia());
    const restored = useGuideSafetyStore();
    assert.equal(restored.hold, true);
    assert.equal(restored.activeEvent, null);
    assert.equal(restored.resumeDemo(), false);
  } finally {
    if (previous === undefined) delete globalThis.sessionStorage; else globalThis.sessionStorage = previous;
  }
});

test("simulated hold does not persist, and unavailable storage does not interrupt a real hold", () => {
  const previous = globalThis.sessionStorage;
  let writes = 0;
  globalThis.sessionStorage = { getItem: () => null, setItem: () => { writes++; throw new Error('storage unavailable'); } };
  try {
    setActivePinia(createPinia());
    const safety = useGuideSafetyStore();
    safety.observeControllerState({ activeSafetyEvent: { simulated: true } });
    assert.equal(writes, 0);
    safety.observeControllerState({ activeSafetyEvent: { simulated: false } });
    assert.equal(writes, 1);
    assert.equal(safety.hold, true);
    assert.equal(safety.simulatedHold, false);
  } finally {
    if (previous === undefined) delete globalThis.sessionStorage; else globalThis.sessionStorage = previous;
  }
});
