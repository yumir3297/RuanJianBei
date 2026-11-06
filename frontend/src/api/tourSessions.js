import http from "./http.js";
import { buildTourBudgetParams } from "../utils/tourBudgetParams.js";

function protectedWrite(csrfToken, idempotencyKey) {
  return {
    withCredentials: true,
    headers: {
      "X-CSRF-Token": csrfToken,
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
    },
  };
}

export async function bootstrapTourSessions() {
  const { data } = await http.get("/tour-sessions/bootstrap", { withCredentials: true });
  return data;
}

export async function fetchTourSessions() {
  const { data } = await http.get("/tour-sessions", { withCredentials: true });
  return data.items || [];
}

export async function fetchTourTrash() {
  const { data } = await http.get("/tour-sessions/trash", { withCredentials: true });
  return data.items || [];
}

export async function fetchTourSession(id) {
  const { data } = await http.get(`/tour-sessions/${encodeURIComponent(id)}`, { withCredentials: true });
  return data;
}

export async function fetchTourRevisions(id) {
  const { data } = await http.get(`/tour-sessions/${encodeURIComponent(id)}/revisions`, { withCredentials: true });
  return data.items || [];
}

export async function restoreTourRevision(id, revisionId, expectedVersion, csrfToken, key) {
  const { data } = await http.post(`/tour-sessions/${encodeURIComponent(id)}/restore/${encodeURIComponent(revisionId)}`,
    null, { ...protectedWrite(csrfToken, key), params: { expected_version: expectedVersion } });
  return data;
}

export async function createTourSession(payload, csrfToken, key) {
  const { data } = await http.post("/tour-sessions", payload, protectedWrite(csrfToken, key));
  return data;
}

export async function saveTourSession(id, payload, csrfToken, key) {
  const { data } = await http.put(`/tour-sessions/${encodeURIComponent(id)}`, payload, protectedWrite(csrfToken, key));
  return data;
}

export async function saveTourSessionV2(id, payload, csrfToken, key) {
  const { data } = await http.put(`/tour-sessions/${encodeURIComponent(id)}/v2`, payload, protectedWrite(csrfToken, key));
  return data;
}
export async function upgradeTourSessionV2(id, version, csrfToken, key) {
  const { data } = await http.post(`/tour-sessions/${encodeURIComponent(id)}/upgrade-v2`, { expected_version: version }, protectedWrite(csrfToken, key));
  return data;
}
export async function fetchTourProgress(id) {
  const { data } = await http.get(`/tour-sessions/${encodeURIComponent(id)}/progress`, { withCredentials: true });
  return data;
}
export async function startTourProgress(id, version, csrfToken, key) {
  const { data } = await http.post(`/tour-sessions/${encodeURIComponent(id)}/start`, { expected_version: version }, protectedWrite(csrfToken, key));
  return data;
}
export async function sendTourProgressCommand(id, version, command, csrfToken, key) {
  const { data } = await http.post(`/tour-sessions/${encodeURIComponent(id)}/progress`, { expected_progress_version: version, command }, protectedWrite(csrfToken, key));
  return data;
}
export async function fetchTourBudget(id, currentStopRemainingMinutes = null) {
  const params = buildTourBudgetParams(currentStopRemainingMinutes);
  const { data } = await http.get(`/tour-sessions/${encodeURIComponent(id)}/budget`, { withCredentials: true, params });
  return data;
}

export async function removeTourSession(id, expectedVersion, csrfToken) {
  const { data } = await http.delete(`/tour-sessions/${encodeURIComponent(id)}`, {
    ...protectedWrite(csrfToken), params: { expected_version: expectedVersion },
  });
  return data;
}

export async function restoreTourSession(id, csrfToken) {
  const { data } = await http.post(`/tour-sessions/${encodeURIComponent(id)}/undelete`, {}, protectedWrite(csrfToken));
  return data;
}

export async function purgeTourSession(id, csrfToken) {
  const { data } = await http.delete(`/tour-sessions/${encodeURIComponent(id)}/purge`, {
    ...protectedWrite(csrfToken), params: { confirm: true },
  });
  return data;
}
