import { API_BASE_URL } from "../api/http";

function parseEventBlock(block) {
  const lines = block.split("\n");
  let event = "message";
  let data = "";

  lines.forEach((line) => {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    }
    if (line.startsWith("data:")) {
      data += line.slice(5).trim();
    }
  });

  return {
    event,
    data: data ? JSON.parse(data) : {},
  };
}

export function useSSEStream() {
  async function postStream(path, payload, handlers = {}, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(payload),
      signal: options.signal,
    });

    if (!response.ok || !response.body) {
      throw new Error("无法建立流式连接。");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        if (!part.trim()) {
          continue;
        }
        const parsed = parseEventBlock(part);
        const handler = handlers[parsed.event];
        if (handler) {
          handler(parsed.data);
        }
      }
    }
  }

  return {
    postStream,
  };
}
