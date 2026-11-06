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

export async function fetchItineraryProposals(id, limit = 10) {
  const { data } = await http.get(`/tour-sessions/${encodeURIComponent(id)}/proposals`, {
    withCredentials: true, params: { limit },
  });
  return data.items || [];
}

export async function retryItineraryProposal(id, jobId, csrfToken, key) {
  const { data } = await http.post(
    `/tour-sessions/${encodeURIComponent(id)}/executions/${encodeURIComponent(jobId)}/retry`,
    { confirm_duplicate_risk: true },
    { withCredentials: true, headers: { "X-CSRF-Token": csrfToken, "Idempotency-Key": key } },
  );
  return data;
}

export async function applyItineraryProposal(id, proposalId, payload, csrfToken, key) {
  const { data } = await http.post(`/tour-sessions/${encodeURIComponent(id)}/proposals/${encodeURIComponent(proposalId)}/apply`, payload, {
    withCredentials: true, headers: { "X-CSRF-Token": csrfToken, "Idempotency-Key": key },
  });
  return data;
}
