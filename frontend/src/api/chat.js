import { useSSEStream } from "../composables/useSSEStream";

export async function streamChat(payload, handlers, options = {}) {
  const { postStream } = useSSEStream();
  return postStream("/api/chat/stream", payload, handlers, options);
}
