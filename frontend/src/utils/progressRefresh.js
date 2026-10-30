export async function refreshProgressAfterPlanSave(sessionId, previousProgress, fetchProgress) {
  if (previousProgress?.status !== "active") return previousProgress;
  try {
    return await fetchProgress(sessionId);
  } catch {
    return null;
  }
}

export async function refreshProgressAfterItineraryApply(sessionId, fetchProgress) {
  try {
    return await fetchProgress(sessionId);
  } catch {
    return null;
  }
}
