import test from "node:test";
import assert from "node:assert/strict";
import { refreshProgressAfterItineraryApply, refreshProgressAfterPlanSave } from "../src/utils/progressRefresh.js";

test("reloads progress after an itinerary apply so commands use the new progress version", async () => {
  const progress = { status: "active", progress_version: 4 };
  const requests = [];
  const actual = await refreshProgressAfterItineraryApply("tour-1", async id => {
    requests.push(id);
    return progress;
  });

  assert.deepEqual(requests, ["tour-1"]);
  assert.equal(actual, progress);
});

test("clears progress when it cannot be refreshed after an itinerary apply", async () => {
  const actual = await refreshProgressAfterItineraryApply("tour-1", async () => {
    throw new Error("offline");
  });

  assert.equal(actual, null);
});

test("reloads active progress after saving a plan revision", async () => {
  const active = { status: "active", progress_version: 4 };
  const refreshed = { status: "active", progress_version: 5 };
  const requests = [];
  const actual = await refreshProgressAfterPlanSave("tour-1", active, async id => {
    requests.push(id);
    return refreshed;
  });

  assert.deepEqual(requests, ["tour-1"]);
  assert.equal(actual, refreshed);
});

test("does not reload progress after a plan save when no active tour can be reconciled", async () => {
  let requested = false;
  const notStarted = { status: "not_started", progress_version: 0 };
  const actual = await refreshProgressAfterPlanSave("tour-1", notStarted, async () => {
    requested = true;
    throw new Error("should not fetch");
  });

  assert.equal(actual, notStarted);
  assert.equal(requested, false);
});
