import http from "./adminHttp.js";

export async function fetchKnowledgeList() {
  const { data } = await http.get("/knowledge/");
  return data;
}

export async function previewKnowledgeUnderstanding(id, payload) {
  const { data } = await http.post(`/knowledge/${id}/understanding-preview`, payload, { timeout: 120000 });
  return data;
}

export async function downloadKnowledgeSource(id, revisionId) {
  const { data } = await http.get(`/knowledge/${id}/source`, { params: { revision_id: revisionId }, responseType: "blob" });
  return data;
}

export async function createKnowledge(payload) {
  const { data } = await http.post("/knowledge/", payload);
  return data;
}

export async function updateKnowledge(id, payload) {
  const { data } = await http.put(`/knowledge/${id}`, payload);
  return data;
}

export async function deleteKnowledge(id) {
  const { data } = await http.delete(`/knowledge/${id}`);
  return data;
}

export async function discardKnowledgeDraft(id) {
  const { data } = await http.delete(`/knowledge/${id}/draft`);
  return data;
}

