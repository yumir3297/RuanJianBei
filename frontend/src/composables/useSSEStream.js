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
    const controller = new AbortController();
    const abortFromCaller = () => controller.abort(options.signal?.reason);
    if (options.signal?.aborted) {
      abortFromCaller();
    } else {
      options.signal?.addEventListener("abort", abortFromCaller, { once: true });
    }

    const connectionTimeoutMs = options.connectionTimeoutMs ?? 20000;
    const connectionTimer = globalThis.setTimeout(() => {
      controller.abort(new DOMException("流式连接建立超时", "TimeoutError"));
    }, connectionTimeoutMs);

    let response;
    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
    } catch (error) {
      options.signal?.removeEventListener("abort", abortFromCaller);
      if (controller.signal.reason?.name === "TimeoutError") {
        throw new Error("导览服务连接超时，请确认后端已就绪后重试。");
      }
      throw error;
    } finally {
      globalThis.clearTimeout(connectionTimer);
    }

    if (!response.ok || !response.body) {
      options.signal?.removeEventListener("abort", abortFromCaller);
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
    let receivedEventCount = 0;

    const dispatchBlock = (block) => {
      if (!block.trim()) return;
      const parsed = parseEventBlock(block);
      receivedEventCount += 1;
      handlers[parsed.event]?.(parsed.data);
    };

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        // Normalize after concatenation so a CRLF split across network chunks
        // cannot prevent event boundaries from being detected.
        buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          dispatchBlock(part);
        }
      }

      buffer += decoder.decode();
      buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
      dispatchBlock(buffer);
      return { receivedEventCount };
    } finally {
      options.signal?.removeEventListener("abort", abortFromCaller);
    }
  }

  return {
    postStream,
  };
}
