import test from "node:test";
import assert from "node:assert/strict";
import { itineraryProposalDiffText } from "../src/utils/itineraryProposalDiff.js";

test("shows the old and proposed stop duration in a changed-stop diff", () => {
  assert.equal(itineraryProposalDiffText({
    kind: "changed",
    before: { name: "灵山大佛", duration_minutes: 20 },
    after: { name: "灵山大佛", duration_minutes: 30 },
  }), "调整灵山大佛：停留时长 20 分钟 → 30 分钟");
});

test("shows the exact before and after values for a changed time constraint", () => {
  assert.equal(itineraryProposalDiffText({
    kind: "constraints",
    before: { available_minutes: 120 },
    after: { available_minutes: 180 },
  }), "调整约束：可用时间 120 分钟 → 180 分钟");
});

test("shows the removed stop's previous duration", () => {
  assert.equal(itineraryProposalDiffText({
    kind: "removed",
    before: { name: "灵山大佛", duration_minutes: 20 },
  }), "移除：灵山大佛（原停留时长 20 分钟）");
});
