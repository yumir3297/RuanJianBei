import test from "node:test";
import assert from "node:assert/strict";
import { createDemoCrowdDecision, createDemoSafetyEvent, createDemoScenarioController, createDemoWeatherDecision, GUIDE_DEMO_SCENARIO } from "../src/guide/scenario.js";

test("showcase scenario requires explicit acknowledgement and resume", () => {
  assert.equal(GUIDE_DEMO_SCENARIO.mode, "simulated");
  assert.equal(GUIDE_DEMO_SCENARIO.steps.filter((step) => step.requires_user_action).length, 2);
  assert.equal(createDemoSafetyEvent().simulated, true);
  assert.equal(createDemoSafetyEvent().source, "simulated_scenario");
});

test("demo follows an explicit warning, acknowledgement, and manual resume sequence", () => {
  const events = [];
  const decisions = [];
  const scenario = createDemoScenarioController({ dispatch: (event) => events.push(event), setDecision: (value, meta) => decisions.push({ value, meta }) });
  assert.equal(scenario.start(), true);
  assert.equal(scenario.getStage(), "awaiting_warning");
  assert.equal(decisions[0].value.action, "short_narration");
  assert.equal(scenario.raiseWarning(), true);
  assert.equal(scenario.getStage(), "awaiting_acknowledgement");
  assert.equal(scenario.resume(), false);
  assert.equal(scenario.acknowledge(), true);
  assert.equal(scenario.getStage(), "awaiting_manual_resume");
  assert.equal(scenario.resume(), true);
  assert.equal(scenario.getStage(), "complete");
  assert.equal(decisions.at(-1).value.action, "short_narration");
  assert.equal(decisions.at(-1).meta.simulated, true);
  assert.deepEqual(events.map((event) => event.type), ["enable", "safety_raised", "safety_cleared"]);
});

test("crowd showcase identifies itself as simulated and asks for confirmation", () => {
  const decision = createDemoCrowdDecision(new Date("2026-11-07T00:00:00Z"));
  assert.equal(decision.data_mode, "demo");
  assert.equal(decision.evidence_status.crowd, "simulated");
  assert.equal(decision.suggestions[0].requires_confirmation, true);
  assert.match(decision.reasons[0], /不代表实时人数/);
});

test("weather adaptation demo is explicitly simulated and cannot raise a safety event", () => {
  const decision = createDemoWeatherDecision(new Date("2026-11-07T00:00:00Z"));
  assert.equal(decision.data_mode, "demo");
  assert.equal(decision.simulated, true);
  assert.equal(decision.weather_adaptation.kind, "precipitation");
  assert.equal(decision.safety_events.length, 0);
  assert.match(decision.weather_adaptation.condition, /小雨/);
});
