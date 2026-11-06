import test from "node:test";
import assert from "node:assert/strict";
import { buildTourBudgetParams } from "../src/utils/tourBudgetParams.js";

test("budget query params omit empty values and preserve explicit zero or positive minutes", () => {
  assert.equal(buildTourBudgetParams(null), undefined);
  assert.equal(buildTourBudgetParams(undefined), undefined);
  assert.deepEqual(buildTourBudgetParams(0), { current_stop_remaining_minutes: 0 });
  assert.deepEqual(buildTourBudgetParams(5), { current_stop_remaining_minutes: 5 });
});
