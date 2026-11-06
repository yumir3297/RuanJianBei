import test from "node:test";
import assert from "node:assert/strict";
import { reconcileDraftAfterAsyncApply } from "../src/utils/proposalApplyState.js";

test("keeps a manual draft edit made while proposal apply is pending", () => {
  const submittedDraft = { stops: [{ name: "石窟" }] };
  const editedDraft = { stops: [{ name: "石窟" }, { name: "新加的休息点" }] };
  const serverSnapshot = { stops: [{ name: "石窟" }, { name: "博物馆" }] };

  const result = reconcileDraftAfterAsyncApply(submittedDraft, editedDraft, serverSnapshot);

  assert.deepEqual(result, { draftSnapshot: editedDraft, hasConcurrentEdits: true });
});

test("uses the server snapshot when no manual edit happened during proposal apply", () => {
  const submittedDraft = { stops: [{ name: "石窟" }] };
  const serverSnapshot = { stops: [{ name: "石窟" }, { name: "博物馆" }] };

  const result = reconcileDraftAfterAsyncApply(submittedDraft, submittedDraft, serverSnapshot);

  assert.deepEqual(result, { draftSnapshot: serverSnapshot, hasConcurrentEdits: false });
});
