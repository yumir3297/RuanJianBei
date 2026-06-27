import http from "./http";

export async function fetchKnowledgeList() {
  const { data } = await http.get("/knowledge/");
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

