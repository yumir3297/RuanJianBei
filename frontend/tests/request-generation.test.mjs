import test from "node:test";
import assert from "node:assert/strict";
import { createRequestGeneration } from "../src/utils/requestGeneration.js";

test("starting a newer request aborts and invalidates the previous generation", () => {
  const requests = createRequestGeneration();
  const first = requests.begin();
  const second = requests.begin();

  assert.equal(first.signal.aborted, true);
  assert.equal(requests.isCurrent(first), false);
  assert.equal(requests.isCurrent(second), true);
});

test("cancel aborts the in-flight request and makes a late response stale", () => {
  const requests = createRequestGeneration();
  const pending = requests.begin();
  requests.cancel();

  assert.equal(pending.signal.aborted, true);
  assert.equal(requests.isCurrent(pending), false);
});

test("finishing an old generation cannot clear a newer request", () => {
  const requests = createRequestGeneration();
  const old = requests.begin();
  const current = requests.begin();

  assert.equal(requests.finish(old), false);
  assert.equal(requests.isCurrent(current), true);
  assert.equal(requests.finish(current), true);
  assert.equal(requests.isCurrent(current), false);
});
