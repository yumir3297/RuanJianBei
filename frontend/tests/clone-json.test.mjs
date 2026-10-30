import test from "node:test";
import assert from "node:assert/strict";
import { cloneJson } from "../src/utils/cloneJson.js";

test("clones JSON snapshots wrapped in a reactive proxy", () => {
  const snapshot = new Proxy({ constraints: { available_minutes: 90 }, stops: [{ name: "大佛" }] }, {});
  assert.throws(() => structuredClone(snapshot), { name: "DataCloneError" });
  const copy = cloneJson(snapshot);
  assert.deepEqual(copy, { constraints: { available_minutes: 90 }, stops: [{ name: "大佛" }] });
  copy.stops[0].name = "已修改";
  assert.equal(snapshot.stops[0].name, "大佛");
});
