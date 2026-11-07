import http from "./adminHttp.js";

export async function uploadKnowledgeFiles(files, { documentId = "" } = {}) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  if (documentId) files.forEach(() => form.append("document_ids", documentId));
  const { data } = await http.post("/knowledge-imports/", form, {
    headers: { "Content-Type": "multipart/form-data", "Idempotency-Key": crypto.randomUUID() },
    timeout: 120000,
  });
  return data;
}

export async function fetchKnowledgeImport(id) {
  const { data } = await http.get(`/knowledge-imports/${id}`);
  return data;
}

export async function fetchRecentKnowledgeImports() {
  const { data } = await http.get("/knowledge-imports/recent");
  return data;
}

export async function retryKnowledgeImport(id) {
  const { data } = await http.post(`/knowledge-imports/${id}/retry`);
  return data;
}

export async function resolveKnowledgeConflict(id, payload) {
  const { data } = await http.post(`/knowledge-imports/conflicts/${id}/resolve`, payload);
  return data;
}
