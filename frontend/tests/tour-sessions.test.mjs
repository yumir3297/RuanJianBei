import test from "node:test";
import assert from "node:assert/strict";
import { getOperationKey } from "../src/utils/tourSessionKeys.js";

test("retrying an unchanged tour operation reuses its idempotency key", () => {
  const cache = {};
  let next = 0;
  const createKey = () => `key-${++next}`;
  const first = getOperationKey(cache, "save:tour-1", { expected_version: 2, snapshot: { stops: [] } }, createKey);
  const retry = getOperationKey(cache, "save:tour-1", { expected_version: 2, snapshot: { stops: [] } }, createKey);
  const changed = getOperationKey(cache, "save:tour-1", { expected_version: 2, snapshot: { stops: [{ name: "大佛" }] } }, createKey);

  assert.equal(retry.key, first.key);
  assert.notEqual(changed.key, first.key);
});
