import http from "./http.js";

export async function fetchItineraryCatalog() {
  const { data } = await http.get("/itinerary/catalog");
  return data;
}

export async function createItineraryProposal(id, payload, csrfToken, key, signal) {
  const { data } = await http.post(`/tour-sessions/${encodeURIComponent(id)}/proposals`, payload, {
    withCredentials: true, headers: { "X-CSRF-Token": csrfToken, "Idempotency-Key": key },
    signal,
  });
  return data;
}

export async function fetchItineraryProposal(id, proposalId, signal) {
  const { data } = await http.get(`/tour-sessions/${encodeURIComponent(id)}/proposals/${encodeURIComponent(proposalId)}`, {
    withCredentials: true,
    signal,
  });
  return data;
}

export async function applyItineraryProposal(id, proposalId, payload, csrfToken, key) {
  const { data } = await http.post(`/tour-sessions/${encodeURIComponent(id)}/proposals/${encodeURIComponent(proposalId)}/apply`, payload, {
    withCredentials: true, headers: { "X-CSRF-Token": csrfToken, "Idempotency-Key": key },
  });
  return data;
}
