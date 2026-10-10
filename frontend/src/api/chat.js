import { useSSEStream } from "../composables/useSSEStream";
import http from "./http";

export async function streamChat(payload, handlers, options = {}) {
  const { postStream } = useSSEStream();
  return postStream("/api/chat/stream", payload, handlers, options);
}

export async function fetchWelcomeAudio() {
  const { data } = await http.get("/chat/welcome-audio");
  return data;
}

/** 清除该游客在服务端的跨会话记忆，返回删除条数。 */
export async function deleteVisitorMemory(visitorId) {
  const { data } = await http.delete(
    `/chat/visitor-memory/${encodeURIComponent(visitorId)}`,
  );
  return data;
}
