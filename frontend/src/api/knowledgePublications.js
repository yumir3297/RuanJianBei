import http from "./http";
import { createIdempotencyKey } from "../utils/idempotencyKey.js";

export async function createKnowledgePublication(items, key = createIdempotencyKey()) {
  const { data } = await http.post("/knowledge-publications/", {
    idempotency_key: key,
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
