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
