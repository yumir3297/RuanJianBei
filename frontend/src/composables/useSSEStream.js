import { API_BASE_URL } from "../api/transport.js";

function parseEventBlock(block) {
  let event = "message";
  const data = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
  }
  // SSE comments and blank heartbeat frames carry no dispatchable event.
  if (!data.length) return null;
  return { event, data: JSON.parse(data.join("\n")) };
}

export function useSSEStream() {
  async function postStream(path, payload, handlers = {}, options = {}) {
    const controller = new AbortController();
    const abortFromCaller = () => controller.abort(options.signal?.reason);
    if (options.signal?.aborted) abortFromCaller();
    else options.signal?.addEventListener("abort", abortFromCaller, { once: true });

    const connectionTimeoutMs = options.connectionTimeoutMs ?? 20000;
    const idleTimeoutMs = options.idleTimeoutMs ?? 45000;
    const progressTimeoutMs = options.progressTimeoutMs ?? 90000;
    const totalTimeoutMs = options.totalTimeoutMs ?? 180000;
    const timers = new Map();
    let reader;
    let completed = false;
    const schedule = (name, ms, message) => {
      globalThis.clearTimeout(timers.get(name));
      if (Number.isFinite(ms) && ms > 0) {
        timers.set(name, globalThis.setTimeout(() => {
          controller.abort(new DOMException(message, "TimeoutError"));
        }, ms));
      }
    };
    const resetIdle = () => schedule("idle", idleTimeoutMs, "导览连接等待数据超时，请重试。");
    const resetProgress = () => schedule("progress", progressTimeoutMs, "导览等待进展超时，请重试。");
    schedule("connection", connectionTimeoutMs, "导览服务连接超时，请重试。");
    schedule("total", totalTimeoutMs, "导览处理时间过长，请重试。");

    try {
      const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...(options.headers || {}) },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      globalThis.clearTimeout(timers.get("connection"));
      timers.delete("connection");
      if (!response.ok || !response.body) {
        let detail = "";
        try {
          const raw = await response.text();
          try { const json = JSON.parse(raw); detail = json?.detail || json?.message || ""; }
          catch { detail = raw; }
        } catch { /* use the HTTP status */ }
        throw new Error(typeof detail === "string" && detail ? detail : `无法建立流式连接（HTTP ${response.status}）。`);
      }

      reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let receivedEventCount = 0;
      let lastStatus = null;
      const dispatchBlock = (block) => {
        if (!block.trim()) return;
        const parsed = parseEventBlock(block);
        if (!parsed) return;
        receivedEventCount += 1;
        const status = parsed.event === "status" ? JSON.stringify(parsed.data) : null;
        if (parsed.event !== "heartbeat" && (parsed.event !== "status" || status !== lastStatus)) resetProgress();
        if (status !== null) lastStatus = status;
        handlers[parsed.event]?.(parsed.data);
      };
      resetIdle();
      resetProgress();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value?.byteLength) resetIdle();
        buffer += decoder.decode(value, { stream: true });
        // Preserve a trailing CR until the next chunk, when it may form CRLF.
        let trailingCR = "";
        if (buffer.endsWith("\r")) { buffer = buffer.slice(0, -1); trailingCR = "\r"; }
        buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
        const parts = buffer.split("\n\n");
        buffer = (parts.pop() || "") + trailingCR;
        for (const part of parts) dispatchBlock(part);
      }
      // Only a blank-line terminated SSE frame is complete. An unterminated
      // final fragment may have been cut off by an interrupted connection.
      completed = true;
      return { receivedEventCount };
    } catch (error) {
      if (controller.signal.reason?.name === "TimeoutError") {
        const timeoutError = new Error(controller.signal.reason.message);
        timeoutError.name = "TimeoutError";
        throw timeoutError;
      }
      throw error;
    } finally {
      for (const timer of timers.values()) globalThis.clearTimeout(timer);
      options.signal?.removeEventListener("abort", abortFromCaller);
      if (reader && !completed) {
        controller.abort();
        await reader.cancel().catch(() => {});
      }
      reader?.releaseLock();
    }
  }
  return { postStream };
}
