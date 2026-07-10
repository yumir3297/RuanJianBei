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
      data += `${data ? "\n" : ""}${line.slice(5).trimStart()}`;
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
      let detail = "";
      try {
        const errorPayload = await response.json();
        detail = errorPayload?.detail || errorPayload?.message || "";
      } catch {
        detail = await response.text().catch(() => "");
      }
      throw new Error(detail || `无法建立流式连接（HTTP ${response.status}）。`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    const dispatchBlock = (block) => {
      if (!block.trim()) return;
      const parsed = parseEventBlock(block);
      handlers[parsed.event]?.(parsed.data);
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        dispatchBlock(part);
      }
    }

    buffer += decoder.decode();
    dispatchBlock(buffer);
  }

  return {
    postStream,
  };
}
