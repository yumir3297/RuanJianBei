import http from "./http";

export async function createKnowledgePublication(items) {
  const { data } = await http.post("/knowledge-publications/", {
    idempotency_key: crypto.randomUUID(),
    items,
  });
  return data;
}

export async function fetchKnowledgePublication(id) {
  const { data } = await http.get(`/knowledge-publications/${id}`);
  return data;
}

export async function retryKnowledgePublication(id) {
  const { data } = await http.post(`/knowledge-publications/${id}/retry`);
  return data;
}
