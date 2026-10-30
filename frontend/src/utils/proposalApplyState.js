import { cloneJson } from "./cloneJson.js";
import { stableSnapshotStringify } from "./proposalSnapshot.js";

export function reconcileDraftAfterAsyncApply(submittedDraft, currentDraft, serverSnapshot) {
  const hasConcurrentEdits = stableSnapshotStringify(currentDraft) !== stableSnapshotStringify(submittedDraft);
  return {
    draftSnapshot: cloneJson(hasConcurrentEdits ? currentDraft : serverSnapshot),
    hasConcurrentEdits,
  };
}
