import http from "./http.js";

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

export async function createTourSession(payload, csrfToken, key) {
  const { data } = await http.post("/tour-sessions", payload, protectedWrite(csrfToken, key));
  return data;
}

export async function saveTourSession(id, payload, csrfToken, key) {
  const { data } = await http.put(`/tour-sessions/${encodeURIComponent(id)}`, payload, protectedWrite(csrfToken, key));
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
