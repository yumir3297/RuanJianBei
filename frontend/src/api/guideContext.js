import http from "./http";

export async function fetchGuideBootstrap() {
  const { data } = await http.get("/guide/bootstrap", { timeout: 8000 });
  return data;
}

export async function requestGuideDecision(payload, { signal } = {}) {
  const { data } = await http.post("/guide/decision", payload, { timeout: 10000, signal });
  return data;
}
