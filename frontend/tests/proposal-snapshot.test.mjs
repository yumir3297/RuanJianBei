import test from "node:test";
import assert from "node:assert/strict";
import { isProposalDraftStale } from "../src/utils/proposalSnapshot.js";

const canonical = '{"schema_version":2,"stops":[{"duration_minutes":30,"stop_id":"s1"}]}';

test("marks a proposal stale when its stop duration no longer matches the draft", () => {
  assert.equal(isProposalDraftStale(canonical, {
    schema_version: 2,
    stops: [{ stop_id: "s1", duration_minutes: 40 }],
  }), true);
});

test("keeps a proposal applicable while its captured draft is unchanged", () => {
  assert.equal(isProposalDraftStale(canonical, {
    stops: [{ duration_minutes: 30, stop_id: "s1" }],
    schema_version: 2,
  }), false);
});

test("does not report a stale proposal when no proposal snapshot exists", () => {
  assert.equal(isProposalDraftStale("", { schema_version: 2, stops: [] }), false);
});
