import http from "./adminHttp.js";
import { useSSEStream } from "../composables/useSSEStream.js";
import { getAdminToken } from "../utils/adminAuthStorage.js";

export async function fetchGuideLoopCases() {
  const { data } = await http.get("/admin/guide-loop/cases");
  return data;
}

export async function createGuideLoopDraft(caseId, payload) {
  const { data } = await http.post(`/admin/guide-loop/cases/${encodeURIComponent(caseId)}/draft`, payload);
  return data;
}

export async function verifyGuideLoopDraft(caseId, draftId) {
  const { data } = await http.post(`/admin/guide-loop/cases/${encodeURIComponent(caseId)}/verify`, { draft_id: draftId });
  return data;
}

export async function publishGuideLoopDraft(caseId, draftId, baseRevision, sourceReviewed) {
  const { data } = await http.post(`/admin/guide-loop/cases/${encodeURIComponent(caseId)}/publish`, { draft_id: draftId, base_revision: baseRevision, source_reviewed: sourceReviewed });
  return data;
}

export async function confirmGuideLoopLive(checkId, passed) {
  const { data } = await http.post("/admin/guide-loop/confirm-live", { check_id: checkId, passed });
  return data;
}

export async function replayGuideLoopQuestion({ query, poiId }) {
  const sessionId = `gl-live-${crypto.randomUUID()}`;
  const result = { text: "", sources: [], context: null, done: null, error: null };
  const handlers = {
    text: (data) => { result.text += data?.text || ""; },
    sources: (data) => { result.sources = data?.docs || []; },
    context: (data) => { result.context = data?.guide_loop || null; },
    done: (data) => { result.done = data || {}; },
    error: (data) => { result.error = data?.message || "SSE 请求失败"; },
  };
  const token = getAdminToken();
  if (!token) throw new Error("请先登录管理端");
  await useSSEStream().postStream("/api/admin/guide-loop/replay", { query, session_id: sessionId, text_only: true, guide_loop: { poi_id: poiId } }, handlers, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!result.text && !result.error) result.error = "流式请求结束前没有收到文本事件";
  return result;
}
